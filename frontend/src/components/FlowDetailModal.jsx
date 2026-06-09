import { X } from "lucide-react";

import Badge from "./Badge";
import Button from "./Button";
import { useLanguage } from "../context/LanguageContext";

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? value : value.toFixed(6);
  return String(value);
}

function endpointLabel(flow) {
  const src = flow.src_port ? `${flow.src_ip ?? "-"}:${flow.src_port}` : flow.src_ip ?? "-";
  const dst = flow.dst_port ? `${flow.dst_ip ?? "-"}:${flow.dst_port}` : flow.dst_ip ?? "-";
  return `${src} -> ${dst}`;
}

export default function FlowDetailModal({ detail, error, isLoading, onClose }) {
  const { t } = useLanguage();
  const flow = detail?.flow;
  const featureRows = flow ? Object.entries(flow.flow_features ?? {}).sort(([left], [right]) => left.localeCompare(right)) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/45 px-4 py-8">
      <div className="w-full max-w-5xl overflow-hidden rounded-lg border border-line bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">{t("Flow detail")}</h2>
            <p className="mt-1 text-sm text-muted">{flow ? endpointLabel(flow) : t("Loading flow")}</p>
          </div>
          <Button variant="ghost" onClick={onClose}>
            <X size={18} />
          </Button>
        </div>

        <div className="grid gap-5 p-5">
          {isLoading ? <div className="text-sm text-muted">{t("Loading...")}</div> : null}
          {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

          {flow ? (
            <>
              <div className="grid gap-3 md:grid-cols-4">
                <Info label={t("Protocol")} value={flow.protocol ?? "-"} />
                <Info label={t("Score")} value={formatValue(flow.anomaly_score)} />
                <Info label={t("Packets")} value={flow.bidirectional_packets ?? "-"} />
                <div className="rounded-lg border border-line bg-panel p-3">
                  <div className="text-xs uppercase text-muted">{t("Prediction")}</div>
                  <div className="mt-2">
                    <Badge tone={flow.prediction === 1 ? "red" : "neutral"}>{flow.prediction === 1 ? "ANOMALY" : "BENIGN"}</Badge>
                  </div>
                </div>
              </div>

              <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
                <div className="overflow-hidden rounded-lg border border-line">
                  <div className="border-b border-line bg-panel px-4 py-3 text-sm font-semibold text-ink">{t("Top numeric deviations")}</div>
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-line text-xs uppercase text-muted">
                      <tr>
                        <th className="px-4 py-3 font-semibold">{t("Feature")}</th>
                        <th className="px-4 py-3 text-right font-semibold">{t("Value")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {detail.explanation.map((item) => (
                        <tr key={item.feature}>
                          <td className="px-4 py-3 font-medium text-ink">{item.feature}</td>
                          <td className="px-4 py-3 text-right text-muted">{formatValue(item.value)}</td>
                        </tr>
                      ))}
                      {detail.explanation.length === 0 ? (
                        <tr>
                          <td className="px-4 py-6 text-muted" colSpan="2">
                            {t("No numeric features for explanation.")}
                          </td>
                        </tr>
                      ) : null}
                    </tbody>
                  </table>
                </div>

                <div className="max-h-[520px] overflow-auto rounded-lg border border-line">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 border-b border-line bg-panel text-xs uppercase text-muted">
                      <tr>
                        <th className="px-4 py-3 font-semibold">{t("Feature")}</th>
                        <th className="px-4 py-3 font-semibold">{t("Value")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-line">
                      {featureRows.map(([key, value]) => (
                        <tr key={key}>
                          <td className="px-4 py-2 font-medium text-ink">{key}</td>
                          <td className="px-4 py-2 text-muted">{formatValue(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-3">
      <div className="text-xs uppercase text-muted">{label}</div>
      <div className="mt-1 font-semibold text-ink">{value}</div>
    </div>
  );
}
