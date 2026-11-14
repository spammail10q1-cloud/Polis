"""A real, in-process federated-learning demonstration.

This is not a production federated system. It demonstrates:
* local client training on synthetic data,
* update norm clipping,
* additive pairwise masking (a simulation of secure aggregation),
* calibrated Gaussian noise with a simple epsilon accountant,
* FedAvg aggregation over masked client updates,
* per-round evaluation on a synthetic holdout set.

No raw health records leave the process. No real participants are involved.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import FederatedTrainingRound, PrivacyBudget, User


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40, 40)))


def _loss_accuracy(weights: np.ndarray, X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    logits = X @ weights
    probabilities = _sigmoid(logits)
    eps = 1e-9
    loss = float(-np.mean(y * np.log(probabilities + eps) + (1 - y) * np.log(1 - probabilities + eps)))
    accuracy = float(np.mean((probabilities >= 0.5).astype(float) == y))
    return round(loss, 4), round(accuracy, 4)


def _make_federation(rng: np.random.Generator, clients: int = 8, samples: int = 64) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray, np.ndarray]:
    # Synthetic, non-clinical task: classify a generated binary pattern from two
    # synthetic physiological-style features. This is not a disease model.
    true_weights = np.array([2.1, -1.6, 0.35])
    client_data: list[tuple[np.ndarray, np.ndarray]] = []
    for client_index in range(clients):
        shift = rng.normal(0, 1.0, 2)
        X = rng.normal(shift, 1.0, size=(samples, 2))
        X = np.column_stack([X, np.ones(samples)])
        logits = X @ true_weights + rng.normal(0, 0.45, samples)
        y = (logits > 0).astype(float)
        client_data.append((X, y))
    test_X = rng.normal(0, 1.0, size=(500, 2))
    test_X = np.column_stack([test_X, np.ones(500)])
    test_y = ((test_X @ true_weights + rng.normal(0, 0.45, 500)) > 0).astype(float)
    return client_data, test_X, test_y


def _local_train(
    X: np.ndarray,
    y: np.ndarray,
    global_weights: np.ndarray,
    *,
    epochs: int = 4,
    learning_rate: float = 0.15,
) -> tuple[np.ndarray, float]:
    weights = global_weights.copy()
    for _ in range(epochs):
        probabilities = _sigmoid(X @ weights)
        gradient = (X.T @ (probabilities - y)) / len(y)
        weights -= learning_rate * gradient
    loss, _ = _loss_accuracy(weights, X, y)
    return weights - global_weights, loss


def _pairwise_masks(weights_shape: tuple[int, ...], participants: int, rng: np.random.Generator) -> list[np.ndarray]:
    """Simulate additive secure-aggregation masks. Masks sum to zero."""
    masks = [np.zeros(weights_shape) for _ in range(participants)]
    for i in range(participants):
        for j in range(i + 1, participants):
            mask = rng.normal(0, 0.5, size=weights_shape)
            masks[i] += mask
            masks[j] -= mask
    return masks


def run_demo_rounds(db: Session, user: User, requested_rounds: int) -> dict:
    budget = db.scalar(select(PrivacyBudget).where(PrivacyBudget.user_id == user.id))
    if budget is None:
        budget = PrivacyBudget(user_id=user.id, epsilon_spent=0.0, epsilon_limit=settings.federated_privacy_budget)
        db.add(budget)
        db.flush()

    remaining = max(0.0, budget.epsilon_limit - budget.epsilon_spent)
    epsilon_per_round = settings.federated_dp_epsilon_per_round
    max_rounds = min(requested_rounds, int(remaining // epsilon_per_round) if epsilon_per_round else requested_rounds)
    if max_rounds <= 0:
        return {
            "status": "privacy_budget_exhausted",
            "rounds": [],
            "epsilon_spent_total": round(budget.epsilon_spent, 3),
            "epsilon_limit": budget.epsilon_limit,
            "privacy_notes": [
                "The demonstration privacy budget is exhausted. No further simulated rounds were run.",
            ],
            "simulation_notice": "This is an in-process demonstration, not production federated learning.",
        }

    seed_material = f"{user.id}|federated-demo-v1|{budget.epsilon_spent:.4f}"
    seed = int.from_bytes(hashlib.sha256(seed_material.encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    client_data, test_X, test_y = _make_federation(rng)
    global_weights = np.zeros(3)
    clipping_norm = 0.8
    noise_sigma = 0.035
    results: list[dict] = []

    last_round = db.scalar(
        select(FederatedTrainingRound.round_number)
        .where(FederatedTrainingRound.user_id == user.id)
        .order_by(FederatedTrainingRound.round_number.desc())
        .limit(1)
    ) or 0

    for local_round in range(max_rounds):
        updates: list[np.ndarray] = []
        local_losses: list[float] = []
        for X, y in client_data:
            delta, loss = _local_train(X, y, global_weights)
            norm = float(np.linalg.norm(delta))
            if norm > clipping_norm:
                delta = delta * (clipping_norm / norm)
            updates.append(delta)
            local_losses.append(loss)

        # Simulated secure aggregation: the server only receives masked vectors.
        masks = _pairwise_masks(global_weights.shape, len(updates), rng)
        masked = [update + mask for update, mask in zip(updates, masks)]
        noise = rng.normal(0, noise_sigma, size=global_weights.shape)
        aggregated = np.sum(masked, axis=0) + noise
        # In a real protocol, the masks sum to zero. The summation above simulates
        # the unmasked aggregate that the server obtains.
        global_weights = global_weights + aggregated / len(updates)
        loss, accuracy = _loss_accuracy(global_weights, test_X, test_y)
        budget.epsilon_spent = round(budget.epsilon_spent + epsilon_per_round, 4)
        round_number = last_round + local_round + 1
        record = FederatedTrainingRound(
            user_id=user.id,
            round_number=round_number,
            participants=len(client_data),
            epsilon=epsilon_per_round,
            loss=loss,
            accuracy=accuracy,
            status="simulated",
            details={
                "task": "synthetic binary pattern classification from two synthetic features",
                "not_clinical": True,
                "aggregation": "FedAvg over masked updates",
                "clipping_norm": clipping_norm,
                "gaussian_noise_sigma": noise_sigma,
                "secure_aggregation": "simulated additive pairwise masks",
                "raw_data_left_process": False,
                "local_losses": [round(value, 4) for value in local_losses],
                "note": "No real participant data, no production secure aggregation, no formal end-to-end DP proof.",
            },
        )
        db.add(record)
        results.append(
            {
                "round": round_number,
                "participants": len(client_data),
                "loss": loss,
                "accuracy": accuracy,
                "epsilon": round(epsilon_per_round, 3),
                "epsilon_spent_cumulative": round(budget.epsilon_spent, 3),
                "mechanism": "FedAvg + clipping + Gaussian noise + simulated pairwise masks",
            }
        )

    db.flush()
    return {
        "status": "simulation_complete",
        "rounds": results,
        "epsilon_spent_total": round(budget.epsilon_spent, 3),
        "epsilon_limit": budget.epsilon_limit,
        "privacy_notes": [
            "Clients train locally on synthetic records; only model updates are aggregated.",
            "Updates are clipped and Gaussian noise is added. The privacy budget uses simple composition, which is conservative and not a full accountant.",
            "Pairwise additive masks are simulated in-process. This is a simulation, not production secure aggregation; no cryptographic protocol or independent security audit is implemented.",
            "Federated learning does not guarantee anonymity. Repeated updates can leak information, and metadata can be sensitive.",
            "This demo uses no real participants and produces no clinical model.",
        ],
        "simulation_notice": (
            "Simulation only: in-process demonstration of federated training mechanics. "
            "Not production federated learning and not clinically validated."
        ),
    }
