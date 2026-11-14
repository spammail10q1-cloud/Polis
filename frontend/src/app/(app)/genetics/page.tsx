"use client";

import { useMemo, useState } from "react";
import { ArrowUpFromLine } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Panel, PanelHeader, PanelBody, LoadError, Skeleton } from "@/components/ui/panel";
import { Badge, EvidenceBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/callout";
import { Sheet } from "@/components/ui/sheet";
import { useQuery } from "@/lib/use-query";
import { useToast } from "@/components/toast";
import { errorMessage, uploadFile } from "@/lib/api";
import type { GeneInfo, GeneticsOverview, Phenotype, Variant } from "@/lib/types";
import { cn, formatDate, titleCase } from "@/lib/format";

type UploadResponse = {
  sample: { id: string; file_name: string | null; variant_count: number };
  annotated_variants: number;
  phenotypes_inferred: number;
  warnings: string[];
  message: string;
};

export default function GeneticsPage() {
  const { data, loading, error, refresh } = useQuery<GeneticsOverview>("/genetics");
  const [selected, setSelected] = useState<Phenotype | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<Variant | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  const geneMap = useMemo(
    () => new Map((data?.gene_catalog ?? []).map((gene) => [gene.symbol, gene])),
    [data?.gene_catalog],
  );

  if (loading && !data) return <GeneticsSkeleton />;
  if (error && !data) return <LoadError message={error} onRetry={refresh} />;
  if (!data) return null;

  const uninterpreted = new Set(data.uninterpreted_genes.map((item) => item.gene));

  return (
    <div className="animate-fade-in">
      <PageHeader
        eyebrow="Pharmacogenomic intelligence, demonstration panel"
        title="Genetics"
        description="Curated star-allele diplotypes and phenotypes with their evidence, limitations and medication context. A raw VCF is annotated but never turned into a clinical phenotype."
        actions={
          <Button variant="primary" onClick={() => setUploadOpen(true)}>
            <ArrowUpFromLine className="h-3.5 w-3.5" aria-hidden="true" />
            Upload VCF
          </Button>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
        <GeneStat label="Pharmacogenes" value={String(data.phenotypes.length)} note="With curated phenotype" />
        <GeneStat label="Variants annotated" value={String(data.variants.length)} note="Across all samples" />
        <GeneStat
          label="Uninterpreted"
          value={String(uninterpreted.size)}
          note="Annotated, no phenotype"
          tone={uninterpreted.size ? "amber" : undefined}
        />
        <GeneStat label="Samples" value={String(data.samples.length)} note="Synthetic or uploaded" />
      </div>

      <Callout tone="warning" title="Demonstration pharmacogenomics" className="mb-4">
        {data.disclaimer}
      </Callout>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {data.gene_catalog.map((gene) => {
          const phenotype = data.phenotypes.find((item) => item.gene === gene.symbol);
          const isUninterpreted = uninterpreted.has(gene.symbol);
          if (!phenotype && !isUninterpreted) {
            return (
              <div key={gene.symbol} className="panel p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="font-mono text-[14px] text-mist">{gene.symbol}</span>
                    <div className="mt-1 font-mono text-[11px] text-dim">{gene.chromosome}</div>
                  </div>
                  <Badge tone="muted">Not tested</Badge>
                </div>
                <div className="mt-3 text-[13px] text-muted">No result available</div>
                <div className="mt-1 text-[12px] leading-relaxed text-dim">
                  This gene is in the curated catalog but has no variant call or curated phenotype in this profile.
                </div>
                <div className="mt-3 border-t border-line pt-2.5 text-[11px] text-amber">Unknown is not normal</div>
              </div>
            );
          }

          const header = (
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="font-mono text-[14px] text-mist">{gene.symbol}</span>
                <div className="mt-1 font-mono text-[11px] text-dim">{gene.chromosome}</div>
              </div>
              {phenotype ? (
                <Badge tone="neutral">{phenotype.diplotype}</Badge>
              ) : (
                <Badge tone="amber">Uninterpreted</Badge>
              )}
            </div>
          );

          if (!phenotype) {
            return (
              <div key={gene.symbol} className="panel p-4">
                {header}
                <p className="mt-3 text-[12px] leading-relaxed text-muted">
                  Variants were annotated, but no validated diplotype or phenotype was assigned.
                </p>
              </div>
            );
          }

          return (
            <div
              key={gene.symbol}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(phenotype)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelected(phenotype);
                }
              }}
              aria-haspopup="dialog"
              className="panel group cursor-pointer p-4 text-left transition-colors hover:border-muted/40"
            >
              {header}
              <div className="mt-3 font-display text-[19px] leading-snug text-mist">{phenotype.phenotype}</div>
              <div className="mt-1 text-[12px] text-dim">
                {(phenotype.guideline ?? phenotype.evidence_level).replaceAll("_", " ")}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {phenotype.medications.slice(0, 2).map((med) => (
                  <span key={med.name} className="chip">
                    {med.name}
                  </span>
                ))}
                {phenotype.medications.length > 2 && <span className="chip">+{phenotype.medications.length - 2}</span>}
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5">
                <span className="text-[11px] text-dim">
                  {phenotype.is_synthetic ? "Synthetic result" : "Uploaded result"}
                </span>
                <span className="text-[11px] text-muted group-hover:text-signal">View details</span>
              </div>
            </div>
          );
        })}
      </div>

      {!data.phenotypes.length && (
        <Panel className="mt-4">
          <PanelBody className="flex flex-col items-center py-12 text-center">
            <h3 className="font-display text-[22px] text-mist">No pharmacogenomic interpretation yet</h3>
            <p className="mt-2 max-w-md text-[13px] leading-relaxed text-muted">
              Upload a VCF to annotate known pharmacogene positions, or explore the demonstration account to see curated
              diplotypes. VCF annotation does not create a clinical phenotype.
            </p>
            <Button onClick={() => setUploadOpen(true)} className="mt-4" variant="secondary">
              Upload a VCF
            </Button>
          </PanelBody>
        </Panel>
      )}

      <div className="mt-4 grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
        <Panel className="min-w-0">
          <PanelHeader
            eyebrow="Variant-level view"
            title="Annotated variants"
            description="Only panel positions in the curated annotation set are shown."
            action={<Badge tone="muted">{data.variants.length} records</Badge>}
          />
          <div
            className="scroll-area overflow-x-auto focus-visible:outline-2 focus-visible:outline-solid focus-visible:-outline-offset-2 focus-visible:outline-signal"
            tabIndex={0}
            role="region"
            aria-label="Annotated variants table. Scroll horizontally to read all columns."
          >
            <table className="w-full min-w-[760px]">
              <caption className="sr-only">Annotated variants</caption>
              <thead>
                <tr className="border-b border-line text-left">
                  {["Gene", "Variant", "Genotype", "Zygosity", "Consequence", "Evidence"].map((heading) => (
                    <th key={heading} scope="col" className="px-4 py-2.5 text-[12px] font-medium text-dim">
                      {heading}
                    </th>
                  ))}
                  <th scope="col" className="px-4 py-2.5" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {data.variants.map((variant) => (
                  <tr
                    key={variant.id}
                    onClick={() => setSelectedVariant(variant)}
                    className="cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-raised/50"
                  >
                    <td className="px-4 py-2.5 font-mono text-[13px] text-mist">{variant.gene}</td>
                    <td className="px-4 py-2.5">
                      <div className="font-mono text-[12px] text-muted">{variant.rsid}</div>
                      <div className="mt-0.5 font-mono text-[11px] text-dim">{variant.star_allele ?? "reference"}</div>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[12px] text-mist">{variant.genotype}</td>
                    <td className="px-4 py-2.5 text-[12px] text-muted">{titleCase(variant.zygosity)}</td>
                    <td className="max-w-[220px] px-4 py-2.5">
                      <div className="text-[12px] leading-relaxed text-muted">
                        {variant.consequence ?? "No data"}
                      </div>
                    </td>
                    <td className="max-w-[220px] px-4 py-2.5 font-mono text-[12px] leading-relaxed text-dim">
                      {variant.evidence_level.replaceAll("_", " ")}
                    </td>
                    <td className="px-4 py-1.5 text-right">
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedVariant(variant);
                        }}
                        aria-label={`View variant ${variant.rsid}`}
                        className="min-h-11 min-w-11 px-2 text-[12px] text-muted hover:text-mist sm:min-h-9"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.variants.length && (
              <div className="px-5 py-10 text-center text-[12px] text-dim">No annotated variants.</div>
            )}
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel>
            <PanelHeader eyebrow="Provenance" title="Samples" />
            <div className="divide-y divide-line">
              {data.samples.map((sample) => (
                <div key={sample.id} className="px-4 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="min-w-0 flex-1 truncate text-[13px] text-mist">{sample.file_name ?? sample.source}</span>
                    <Badge tone={sample.is_synthetic ? "amber" : "neutral"} className="shrink-0">
                      {sample.is_synthetic ? "Synthetic" : "Uploaded"}
                    </Badge>
                  </div>
                  <div className="mt-1.5 grid grid-cols-2 gap-1 font-mono text-[11px] text-dim">
                    <span>{sample.variant_count} variants</span>
                    <span className="text-right">{sample.genome_build ?? "Build unknown"}</span>
                    <span>{formatDate(sample.created_at)}</span>
                    <span className="text-right">{sample.status.replaceAll("_", " ")}</span>
                  </div>
                </div>
              ))}
              {!data.samples.length && <div className="px-4 py-8 text-[12px] text-dim">No genetic sample has been added.</div>}
            </div>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Clinical boundary" title="How to read a result" />
            <PanelBody>
              <ul className="list-disc space-y-2.5 pl-4 marker:text-amber/60">
                {[
                  "A phenotype is a predicted enzyme function, not a measurement of activity.",
                  "Relevance depends on the medicine, dose, interactions, organ function and indication.",
                  "A genotype does not capture adherence, environment or clinical status.",
                  "Clinical use requires an accredited laboratory and professional interpretation.",
                ].map((item) => (
                  <li key={item} className="text-[12px] leading-relaxed text-muted">
                    {item}
                  </li>
                ))}
              </ul>
            </PanelBody>
          </Panel>
        </div>
      </div>

      <Sheet
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected?.gene ?? "Gene"}
        eyebrow="Curated pharmacogenomic phenotype"
      >
        {selected && <PhenotypeDetail phenotype={selected} gene={geneMap.get(selected.gene)} />}
      </Sheet>

      <Sheet
        open={Boolean(selectedVariant)}
        onClose={() => setSelectedVariant(null)}
        title={selectedVariant?.rsid ?? "Variant"}
        eyebrow={
          selectedVariant
            ? `${selectedVariant.gene}, ${selectedVariant.star_allele ?? "annotation"}`
            : undefined
        }
        width="max-w-xl"
      >
        {selectedVariant && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-px border border-line bg-line">
              {[
                ["Genotype", selectedVariant.genotype],
                ["Zygosity", titleCase(selectedVariant.zygosity)],
                ["Chromosome", selectedVariant.chromosome ?? "No data"],
                ["Position", selectedVariant.position?.toLocaleString() ?? "No data"],
                ["Reference", selectedVariant.ref ?? "No data"],
                ["Alternate", selectedVariant.alt ?? "No data"],
              ].map(([label, value]) => (
                <div key={label} className="bg-panel px-3 py-2.5">
                  <div className="mono-label">{label}</div>
                  <div className="mt-1 font-mono text-[12px] text-mist">{value}</div>
                </div>
              ))}
            </div>
            <div>
              <div className="mono-label mb-1.5">Annotation</div>
              <p className="text-[13px] leading-relaxed text-muted">
                {selectedVariant.interpretation ?? "No interpretation recorded."}
              </p>
            </div>
            <div>
              <div className="mono-label mb-1.5">Evidence level</div>
              <p className="text-[13px] text-muted">{selectedVariant.evidence_level.replaceAll("_", " ")}</p>
            </div>
            <Callout tone="warning" title="Not a clinical diplotype">
              This annotation covers a known variant position only. Phasing, copy-number variation and rare alleles are
              not assessed. POLIS does not convert this record into a phenotype.
            </Callout>
          </div>
        )}
      </Sheet>

      <UploadVcfSheet open={uploadOpen} onClose={() => setUploadOpen(false)} onUploaded={refresh} />
    </div>
  );
}

function PhenotypeDetail({ phenotype, gene }: { phenotype: Phenotype; gene?: GeneInfo }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-mono text-[12px] text-dim">{phenotype.diplotype}</div>
          <h3 className="mt-1.5 font-display text-[28px] leading-tight text-mist">{phenotype.phenotype}</h3>
          <div className="mt-2.5 flex flex-wrap gap-2">
            <EvidenceBadge value={phenotype.evidence_level} className="max-w-full whitespace-normal text-left" />
            {phenotype.is_synthetic && <Badge tone="amber">Synthetic curated result</Badge>}
          </div>
        </div>
        {phenotype.activity_score !== null && (
          <div className="border border-line px-3 py-2.5 text-right">
            <div className="mono-label">Activity score</div>
            <div className="mt-1 number text-[24px] text-mist">{phenotype.activity_score}</div>
            <div className="mt-0.5 text-[11px] text-dim">Interpretation tier</div>
          </div>
        )}
      </div>

      {gene && (
        <div className="border border-line bg-ink p-4">
          <div className="text-[13px] text-mist">{gene.name}</div>
          <p className="mt-2 text-[13px] leading-relaxed text-muted">{gene.role}</p>
          <p className="mt-1.5 text-[12px] leading-relaxed text-dim">{gene.complexity}</p>
        </div>
      )}

      <div>
        <div className="mono-label mb-2">Interpretation</div>
        <p className="text-[13px] leading-relaxed text-muted">{phenotype.interpretation}</p>
      </div>

      <div>
        <div className="mono-label mb-2">Medication context</div>
        <div className="space-y-2">
          {phenotype.medications.map((med) => (
            <div key={med.name} className="border border-line bg-ink px-3 py-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[13px] text-mist">{med.name}</span>
                <span className="font-mono text-[11px] text-dim">{med.status.replaceAll("_", " ")}</span>
              </div>
              <p className="mt-1 text-[12px] leading-relaxed text-muted">{med.relevance}</p>
            </div>
          ))}
          {!phenotype.medications.length && <p className="text-[12px] text-dim">No medication context listed.</p>}
        </div>
      </div>

      <div>
        <div className="mono-label mb-2">Evidence and guideline</div>
        <p className="text-[13px] text-muted">
          {(phenotype.guideline ?? phenotype.evidence_level).replaceAll("_", " ")}
        </p>
      </div>

      <Callout tone="warning" title="Limitations">
        {phenotype.limitations}
      </Callout>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3">
        <span className="font-mono text-[11px] text-dim">{phenotype.source.replaceAll("_", " ")}</span>
        <span className="font-mono text-[11px] text-dim">Updated {formatDate(phenotype.updated_at)}</span>
      </div>
    </div>
  );
}

function UploadVcfSheet({ open, onClose, onUploaded }: { open: boolean; onClose: () => void; onUploaded: () => void }) {
  const { push } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const response = await uploadFile<UploadResponse>("/genetics/upload", file);
      setResult(response);
      push(`${response.annotated_variants} variant${response.annotated_variants === 1 ? "" : "s"} annotated. No phenotype inferred.`, "success");
      onUploaded();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title="Upload a VCF" eyebrow="Conservative annotation only" width="max-w-xl">
      <form onSubmit={submit} className="space-y-4">
        <div className="border border-line bg-ink p-4">
          <div className="text-[13px] text-mist">What POLIS will do</div>
          <ul className="mt-3 list-disc space-y-2 pl-4 marker:text-dim">
            {[
              "Read a UTF-8 text VCF and annotate known panel positions for 11 pharmacogenes.",
              "Store the annotated genotype, zygosity and evidence level with provenance.",
              "Never call a diplotype or phenotype from a raw VCF.",
              "Flag that validated phasing, copy-number and rare-variant analysis are required.",
            ].map((item) => (
              <li key={item} className="text-[12px] leading-relaxed text-muted">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <label className="block cursor-pointer border border-dashed border-line bg-ink px-4 py-8 text-center transition-colors hover:border-muted/40 focus-within:outline-2 focus-within:outline-solid focus-within:outline-offset-2 focus-within:outline-signal">
          <span className="block text-[13px] text-mist">{file ? file.name : "Choose a .vcf file"}</span>
          <span className="mt-1 block font-mono text-[11px] text-dim">UTF-8 VCF, max 25 MB</span>
          <input type="file" accept=".vcf,.txt,text/plain" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="sr-only" />
        </label>

        {error && (
          <div className="border border-danger/25 bg-danger/[0.05] px-3 py-2 text-[12px] text-danger">{error}</div>
        )}

        {result && (
          <div className="space-y-2 border border-mint/25 bg-mint/[0.03] p-3">
            <div className="text-[12px] text-mint">
              Annotated variants: {result.annotated_variants}. Phenotypes inferred: {result.phenotypes_inferred}.
            </div>
            <p className="text-[12px] leading-relaxed text-muted">{result.message}</p>
            {result.warnings.map((warning) => (
              <p key={warning} className="border-t border-line pt-2 text-[11px] leading-relaxed text-dim">
                {warning}
              </p>
            ))}
          </div>
        )}

        <Callout tone="danger" title="Do not use this for clinical decisions">
          A VCF is not a clinical pharmacogenomic report. Do not change medication based on annotated variants. A
          validated laboratory result and professional interpretation are required.
        </Callout>

        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Button type="submit" variant="primary" loading={uploading} disabled={!file}>
            Annotate VCF
          </Button>
        </div>
      </form>
    </Sheet>
  );
}

function GeneStat({ label, value, note, tone }: { label: string; value: string; note: string; tone?: "amber" }) {
  return (
    <div className="bg-panel px-4 py-3">
      <div className="mono-label">{label}</div>
      <div className={cn("mt-1.5 number text-[20px]", tone === "amber" ? "text-amber" : "text-mist")}>{value}</div>
      <div className="mt-0.5 text-[11px] text-dim">{note}</div>
    </div>
  );
}

function GeneticsSkeleton() {
  return (
    <div>
      <Skeleton className="mb-3 h-3 w-56" />
      <Skeleton className="mb-8 h-10 w-[300px]" />
      <Skeleton className="mb-4 h-16 w-full" />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-[190px]" />
        ))}
      </div>
    </div>
  );
}
