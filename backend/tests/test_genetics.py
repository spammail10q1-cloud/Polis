from __future__ import annotations


def test_demo_genetics_overview(demo_client):
    response = demo_client.get("/api/v1/genetics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["phenotypes"]) == 10
    assert len(data["variants"]) == 13
    assert len(data["gene_catalog"]) == 11
    assert any(p["gene"] == "CYP2D6" and p["phenotype"] == "Intermediate metabolizer" for p in data["phenotypes"])
    assert "not a clinical genetic test" in data["disclaimer"].lower()
    assert all(p["is_synthetic"] for p in data["phenotypes"])


def test_vcf_annotation_never_infers_phenotype(make_account):
    client, _ = make_account("vcf")
    vcf = "\n".join(
        [
            "##fileformat=VCFv4.2",
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
            "10\t94781859\trs4244285\tG\tA\t.\tPASS\t.\tGT\t0/1",
            "22\t42128945\trs3892097\tC\tT\t.\tPASS\t.\tGT\t0/1",
        ]
    )
    upload = client.post(
        "/api/v1/genetics/upload",
        files={"file": ("panel.vcf", vcf.encode(), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["annotated_variants"] == 2
    assert body["phenotypes_inferred"] == 0
    assert any("not infer" in warning.lower() or "not a clinical" in warning.lower() for warning in body["warnings"])

    overview = client.get("/api/v1/genetics").json()
    assert overview["phenotypes"] == []
    assert len(overview["variants"]) == 2
    assert any(item["gene"] == "CYP2C19" for item in overview["uninterpreted_genes"])
    genotype_values = {v["gene"]: v["genotype"] for v in overview["variants"]}
    assert genotype_values["CYP2C19"] == "A/G"
    assert genotype_values["CYP2D6"] == "C/T"


def test_malformed_vcf_rejected(make_account):
    client, _ = make_account("bad-vcf")
    response = client.post(
        "/api/v1/genetics/upload",
        files={"file": ("bad.vcf", b"not a vcf", "text/plain")},
    )
    assert response.status_code == 422


def test_genetic_samples_are_tenant_isolated(make_account):
    client_a, _ = make_account("gene-a")
    client_b, _ = make_account("gene-b")
    vcf = "\n".join(
        [
            "##fileformat=VCFv4.2",
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
            "10\t94781859\trs4244285\tG\tA\t.\tPASS\t.\tGT\t0/1",
        ]
    )
    uploaded = client_a.post(
        "/api/v1/genetics/upload", files={"file": ("mine.vcf", vcf.encode(), "text/plain")}
    )
    assert uploaded.status_code == 201
    sample_id = uploaded.json()["sample"]["id"]
    assert client_b.get("/api/v1/genetics").json()["variants"] == []
    assert client_b.delete(f"/api/v1/genetics/samples/{sample_id}").status_code == 404
