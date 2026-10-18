"use client";

import { useState } from "react";

import { FilterChip } from "@/components/ui/FilterChip";
import { FilterRow } from "@/components/ui/FilterRow";
import { LoadMore } from "@/components/ui/LoadMore";
import { SaveButton } from "@/components/ui/SaveButton";
import { StarRatingInput } from "@/components/ui/StarRatingInput";

const loaders = ["Fabric", "Forge", "NeoForge", "Quilt", "Vanilla"];
const versions = ["1.21.4", "1.21.1", "1.20.6", "1.20.1", "1.19.4", "1.18.2", "1.16.5"];

/** Stateful controls: filter chips, save, rating input, «show more». */
export function ControlDemos() {
  const [loader, setLoader] = useState("Fabric");
  const [selectedVersions, setSelectedVersions] = useState<string[]>(["1.21.4"]);
  const [loading, setLoading] = useState(false);

  function toggleVersion(version: string) {
    setSelectedVersions((current) =>
      current.includes(version) ? current.filter((v) => v !== version) : [...current, version],
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <FilterRow label="Лоадер">
        {loaders.map((item) => (
          <FilterChip key={item} active={loader === item} onClick={() => setLoader(item)}>
            {item}
          </FilterChip>
        ))}
      </FilterRow>
      <FilterRow label="Версія гри">
        {versions.map((version) => (
          <FilterChip
            key={version}
            active={selectedVersions.includes(version)}
            onClick={() => toggleVersion(version)}
          >
            {version}
          </FilterChip>
        ))}
      </FilterRow>
      <div className="flex flex-wrap items-center gap-4">
        <SaveButton />
        <SaveButton defaultSaved />
        <SaveButton defaultSaved count={128} />
        <SaveButton disabled />
      </div>
      <StarRatingInput label="Твоя оцінка" name="demo-rating" defaultValue={4} />
      <LoadMore
        loading={loading}
        onClick={() => {
          setLoading(true);
          setTimeout(() => setLoading(false), 1500);
        }}
      />
    </div>
  );
}
