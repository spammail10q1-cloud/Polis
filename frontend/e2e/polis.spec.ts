import { expect, test } from "@playwright/test";

async function loginDemo(page: import("@playwright/test").Page) {
  const response = await page.request.post("/api/v1/auth/demo");
  expect(response.ok()).toBeTruthy();
}

test("demo login loads a coherent synthetic overview", async ({ page }) => {
  await loginDemo(page);
  await page.goto("/overview");
  await expect(page.getByRole("heading", { name: /Welcome back, Avery/i })).toBeVisible();
  await expect(page.getByText(/Demonstration data/i).first()).toBeVisible();
  await expect(page.getByText(/not real patient information/i).first()).toBeVisible();
  await expect(page.getByText("Interactive biological twin")).toBeVisible();
  await expect(page.getByText("No overall health score is calculated.")).toBeVisible();
  await expect(page.getByText("ALT", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/No overall health score is calculated/i)).toBeVisible();
});

test("What If? returns a pathway estimate with interaction and uncertainty", async ({ page }) => {
  await loginDemo(page);
  await page.goto("/what-if?med=clopidogrel");
  const runButton = page.getByRole("button", { name: /Run experimental analysis/i });
  await expect(runButton).toBeEnabled({ timeout: 20_000 });
  await runButton.click();
  await expect(page.getByText(/MAJOR INTERACTION: OMEPRAZOLE/i)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/Relative active-metabolite formation potential/i).first()).toBeVisible();
  await expect(page.getByText(/No dose calculation performed/i).first()).toBeVisible();
  await expect(page.getByText(/5-95%/i).first()).toBeVisible();
  await expect(page.getByText("Unknown").first()).toBeVisible();
  await expect(page.getByText(/not an efficacy prediction/i).first()).toBeVisible();
  await expect(page.getByText(/From hypothetical input to modeled output/i)).toBeVisible();
  await expect(page.getByText(/Sensitivity analysis/i).first()).toBeVisible();
  await expect(page.getByText(/Published parameters and cited assumptions/i)).toBeVisible();
});

test("the assistant grounds an ALT answer in the record and cites a source", async ({ page }) => {
  await loginDemo(page);
  await page.goto("/assistant");
  await page.getByRole("button", { name: /Why is my ALT higher than last time/i }).first().click();
  await expect(page.getByText("48 U/L", { exact: false }).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Sources", { exact: false }).first()).toBeVisible();
  await expect(page.getByText(/American College of Gastroenterology/i).first()).toBeVisible();
  await expect(page.getByText(/POLIS AI is not a clinician/i).first()).toBeVisible();
});

test("privacy settings expose consent, inventory and export", async ({ page }) => {
  await loginDemo(page);
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { name: "Privacy & Data" })).toBeVisible();
  await expect(page.getByText("What you consent to")).toBeVisible();
  await expect(page.getByRole("heading", { name: "What is stored" })).toBeVisible();
  await expect(page.getByText(/No compliance badge/i)).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /Export JSON/i }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain("polis-export");
});

test("mobile navigation and responsive overview work at 390px", async ({ page }) => {
  await loginDemo(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/overview");
  await expect(page.getByRole("heading", { name: /Welcome back, Avery/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /Open navigation/i })).toBeVisible();
  await page.getByRole("button", { name: /Open navigation/i }).click();
  await expect(page.getByRole("link", { name: "Digital Twin" }).last()).toBeVisible();
  await expect(page.getByRole("link", { name: "Privacy & Data" }).last()).toBeVisible();
  await page.getByRole("link", { name: "Digital Twin" }).last().click();
  await expect(page.getByRole("heading", { name: "The digital body" })).toBeVisible();
});

test("registration creates an empty account and photographs the onboarding state", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByPlaceholder("Your name").fill("E2E Person");
  await page.getByPlaceholder("you@example.com").fill(email);
  await page.getByPlaceholder("Create a strong password").fill("StrongPass123");
  await page.getByText(/I accept the terms and privacy notice/i).click();
  await page.getByRole("button", { name: /Create account/i }).click();
  await expect(page.getByText(/Welcome back, E2E/i)).toBeVisible();
  await expect(page.getByText(/0 laboratory signals/i)).toBeVisible();
  await page.goto("/assistant");
  await expect(page.getByText(/AI processing consent is off/i)).toBeVisible();
});

test("manual laboratory entry validates and appears in the longitudinal record", async ({ page }) => {
  const email = `lab-ui-${Date.now()}@example.com`;
  const registered = await page.request.post("/api/v1/auth/register", {
    data: {
      email,
      password: "StrongPass123",
      name: "Lab UI Person",
      accept_terms: true,
      ai_processing: false,
      research_participation: false,
    },
  });
  expect(registered.status()).toBe(201);
  await page.goto("/biomarkers");
  await expect(page.getByText("No laboratory results yet")).toBeVisible();
  await page.getByRole("button", { name: /Add result/i }).first().click();
  await expect(page.getByRole("heading", { name: "Add a laboratory result" })).toBeVisible();
  const numberInputs = page.locator('input[type="number"]');
  await numberInputs.nth(0).fill("52");
  await numberInputs.nth(1).fill("7");
  await numberInputs.nth(2).fill("35");
  await page.getByRole("button", { name: "Add result" }).last().click();
  await expect(page.getByText(/Laboratory result added/i).first()).toBeVisible();
  await expect(page.getByRole("cell", { name: /Alanine aminotransferase/i })).toBeVisible();
  await expect(page.getByText("52", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Above interval").first()).toBeVisible();
});

test("federated demonstration requires opt-in and produces a privacy-ledger result", async ({ page }) => {
  await loginDemo(page);
  await page.request.patch("/api/v1/privacy/consent", { data: { federated_learning: false } });
  await page.goto("/privacy");
  const toggle = page.getByRole("switch", { name: "Federated learning" });
  await toggle.scrollIntoViewIfNeeded();
  await toggle.click();
  await expect(page.getByText(/Federated learning enabled/i).first()).toBeVisible();
  await page.getByRole("button", { name: "Federated lab" }).click();
  await page.getByRole("button", { name: /Run 1 round/i }).click();
  await expect(page.getByText(/simulation complete/i).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/Clients train locally on synthetic records/i)).toBeVisible();
  await expect(page.getByText(/SIMULATION ONLY/i).first()).toBeVisible();
  await page.request.patch("/api/v1/privacy/consent", { data: { federated_learning: false } });
});

test("causal lab exposes the DAG, assumptions and a counterfactual estimate", async ({ page }) => {
  await loginDemo(page);
  await page.goto("/insights");
  await page.getByRole("button", { name: "Causal lab" }).click();
  await expect(page.getByText(/A hypothesis laboratory, not a causal oracle/i)).toBeVisible();
  await expect(page.getByText(/do\(sleep_duration/i)).toBeVisible();
  await page.getByRole("button", { name: /Run exploratory model/i }).click();
  await expect(page.getByText(/Counterfactual estimate/i).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/5th to 95th percentile interval/i).first()).toBeVisible();
  await expect(page.getByText(/not evidence that changing sleep or steps causes/i)).toBeVisible();
  await expect(page.getByText(/Directed acyclic graph used by this query/i)).toBeVisible();
  await expect(page.getByText(/Alternative explanations/i)).toBeVisible();
});

test("a user can import wearable data through the UI", async ({ page }) => {
  const email = `wear-ui-${Date.now()}@example.com`;
  const registered = await page.request.post("/api/v1/auth/register", {
    data: {
      email,
      password: "StrongPass123",
      name: "Wearable Importer",
      accept_terms: true,
      ai_processing: false,
      research_participation: false,
    },
  });
  expect(registered.status()).toBe(201);
  await page.goto("/wearables");
  await page.getByRole("button", { name: /Import data/i }).click();
  const today = new Date().toISOString().slice(0, 10);
  const csv = `metric,value,unit,date,source\nsleep_duration,7.4,h,${today},UI export\nhrv,53,ms,${today},UI export\n`;
  await page.locator('input[type="file"]').last().setInputFiles({
    name: "wearables.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await page.getByRole("button", { name: /Import CSV/i }).click();
  await expect(page.getByText(/2 imported/i).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/user-supplied device estimates/i).first()).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).last().click();
  await expect(page.getByText(/Manual CSV import/i).first()).toBeVisible();
});
