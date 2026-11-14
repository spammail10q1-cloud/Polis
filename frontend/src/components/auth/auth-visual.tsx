"use client";

import { Logo } from "@/components/logo";

export function AuthVisual() {
  return (
    <div className="relative hidden min-h-screen flex-col border-l border-line bg-ink pt-20 lg:flex">
      <div className="flex items-center justify-between gap-4 border-y border-line px-8 py-3 text-[12px] text-dim">
        <span>Anatomic navigation model</span>
        <span>Demonstration data</span>
      </div>

      <div className="flex flex-1 items-center justify-center px-8 py-8 xl:px-12">
        <figure className="w-full max-w-[520px]">
          <div className="panel">
            <div className="flex items-baseline justify-between gap-4 border-b border-line px-5 py-3.5">
              <span className="font-display text-[21px] italic leading-none text-mist">Anatomic plate</span>
              <span className="text-[11px] text-dim">Anterior view</span>
            </div>

            <div className="relative h-[480px] px-5 py-4 xl:h-[560px]">
              <img
                src="/anatomy/body-organs.svg"
                alt="Anatomical illustration of the human organs, anterior view."
                width={600}
                height={1000}
                fetchPriority="high"
                className="absolute inset-x-0 top-4 mx-auto h-[calc(100%-2rem)] w-auto max-w-full object-contain"
                style={{
                  filter: "grayscale(0.85) sepia(0.1) brightness(0.72) contrast(1.2)",
                  opacity: 0.9,
                }}
              />

              <div className="absolute right-0 top-[22%] w-[160px] border border-line bg-panel px-3 py-2.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-muted">CYP2C19</span>
                  <span className="text-[11px] text-violet">Intermediate</span>
                </div>
                <p className="mt-1.5 font-mono text-[12px] text-mist">*1/*2</p>
                <p className="mt-1 text-[11px] text-dim">Demonstration genotype</p>
              </div>

              <div className="absolute left-0 top-[44%] w-[140px] border border-line bg-panel px-3 py-2.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-muted">ALT</span>
                  <span className="text-[11px] text-amber">Above interval</span>
                </div>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="number text-[18px] text-mist">48</span>
                  <span className="font-mono text-[11px] text-dim">U/L</span>
                </div>
                <p className="mt-1 text-[11px] text-dim">Demonstration value</p>
              </div>

              <div className="absolute right-0 top-[56%] w-[148px] border border-line bg-panel px-3 py-2.5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[12px] text-muted">eGFR</span>
                  <span className="text-[11px] text-mint">Within interval</span>
                </div>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="number text-[18px] text-mist">94</span>
                  <span className="font-mono text-[11px] text-dim">mL/min/1.73m²</span>
                </div>
                <p className="mt-1 text-[11px] text-dim">Demonstration value</p>
              </div>
            </div>
          </div>

          <figcaption className="mt-3 flex flex-col gap-1.5 text-[12px] leading-relaxed text-dim sm:flex-row sm:items-baseline sm:justify-between">
            <span>Anatomic navigation model. Not a medical scan.</span>
            <a
              href="https://commons.wikimedia.org/wiki/File:202403_human_anatomy_organs.svg"
              target="_blank"
              rel="noreferrer noopener"
              className="shrink-0 text-[11px] text-dim underline decoration-line underline-offset-2 hover:text-muted"
            >
              Anatomy: DBCLS, CC BY 4.0
            </a>
          </figcaption>
        </figure>
      </div>

      <p className="border-t border-line px-8 py-4 text-[12px] leading-relaxed text-dim">
        Annotated values are demonstration data. They do not describe this visitor, and they are not a diagnosis.
      </p>
    </div>
  );
}

export function AuthTopBar() {
  return (
    <div className="absolute left-0 right-0 top-0 z-20 flex items-center justify-between px-6 py-5 sm:px-10">
      <Logo />
      <span className="hidden text-[12px] text-dim sm:inline">Private by design</span>
    </div>
  );
}
