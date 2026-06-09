import { ArrowLeft, Download, FileText, ListFilter, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { captureWebSocketUrl, createReport, downloadFlowsCsv, getCaptureAnalytics, getFlowDetail } from "../api/captures";
import Badge from "../components/Badge";
import Button from "../components/Button";
import FlowDetailModal from "../components/FlowDetailModal";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

function statusTone(status) {
  if (status === "completed") return "green";
  if (status === "failed") return "red";
  if (status === "running" || status === "stopping") return "blue";
  return "amber";
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`;
}

function formatScore(value) {
  return Number(value ?? 0).toFixed(4);
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime()) || date.getFullYear() <= 1971) return "-";
  return date.toLocaleString();
}

function endpointLabel(flow) {
  const src = flow.src_port ? `${flow.src_ip ?? "-"}:${flow.src_port}` : flow.src_ip ?? "-";
  const dst = flow.dst_port ? `${flow.dst_ip ?? "-"}:${flow.dst_port}` : flow.dst_ip ?? "-";
  return `${src} -> ${dst}`;
}

export default function CaptureDetail() {
  const { t } = useLanguage();
  const { captureId } = useParams();
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [selectedFlowDetail, setSelectedFlowDetail] = useState(null);
  const [flowDetailError, setFlowDetailError] = useState("");
  const [isFlowDetailLoading, setIsFlowDetailLoading] = useState(false);

  const capture = analytics?.capture;
  const captureStatus = capture?.status;
  const summary = analytics?.summary;
  const scoreBuckets = useMemo(
    () =>
      analytics?.score_distribution?.map((bucket) => ({
        range: `${formatScore(bucket.min_score)}-${formatScore(bucket.max_score)}`,
        count: bucket.count,
      })) ?? [],
    [analytics],
  );

  const loadAnalytics = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      setAnalytics(await getCaptureAnalytics(captureId));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, [captureId]);

  async function handleExport() {
    setError("");
    try {
      const blob = await downloadFlowsCsv(captureId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${captureId}_flows.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleGenerateReport() {
    setError("");
    setNotice("");
    setIsGeneratingReport(true);
    try {
      const report = await createReport(captureId, "pdf");
      setNotice(t("Report generated: {id}", { id: report.id }));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsGeneratingReport(false);
    }
  }

  async function openFlowDetail(flow) {
    setSelectedFlowDetail(null);
    setFlowDetailError("");
    setIsFlowDetailLoading(true);
    try {
      setSelectedFlowDetail(await getFlowDetail(captureId, flow.id));
    } catch (requestError) {
      setFlowDetailError(requestError.message);
    } finally {
      setIsFlowDetailLoading(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    if (!["pending", "running", "stopping"].includes(capture?.status)) {
      return undefined;
    }

    const intervalId = window.setInterval(loadAnalytics, 3000);
    return () => window.clearInterval(intervalId);
  }, [capture?.status, loadAnalytics]);

  useEffect(() => {
    if (!captureStatus || !["pending", "running", "stopping"].includes(captureStatus)) {
      return undefined;
    }

    const socket = new window.WebSocket(captureWebSocketUrl(captureId));
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type !== "capture") return;
      setAnalytics((current) => {
        if (!current) return current;
        return {
          ...current,
          capture: message.capture,
          summary: {
            ...current.summary,
            total_flows: message.capture.flows_total,
            anomaly_flows: message.capture.flows_anomaly,
            anomaly_rate: message.capture.flows_total
              ? (message.capture.flows_anomaly / message.capture.flows_total) * 100
              : current.summary.anomaly_rate,
          },
        };
      });
      if (["completed", "failed", "stopped"].includes(message.capture.status)) {
        loadAnalytics();
      }
    };
    socket.onerror = () => {
      socket.close();
    };
    return () => socket.close();
  }, [captureStatus, captureId, loadAnalytics]);

  return (
    <>
      <PageHeader
        title={capture?.name ?? capture?.source_filename ?? t("Capture detail")}
        description={capture ? `${capture.mode} · ${capture.id}` : t("Loading capture data")}
        actions={
          <>
            <Link to="/captures">
              <Button>
                <ArrowLeft size={16} />
                {t("Back")}
              </Button>
            </Link>
            <Button onClick={loadAnalytics}>
              <RefreshCw size={16} />
              {t("Refresh")}
            </Button>
            <Button onClick={handleExport}>
              <Download size={16} />
              {t("Export CSV")}
            </Button>
            <Button onClick={handleGenerateReport} disabled={isGeneratingReport || capture?.status !== "completed"}>
              <FileText size={16} />
              {isGeneratingReport ? t("Generating") : t("Report")}
            </Button>
            <Link to={`/captures/${captureId}/flows`}>
              <Button variant="primary">
                <ListFilter size={16} />
                {t("All flows")}
              </Button>
            </Link>
          </>
        }
      />

      <section className="grid gap-5 p-5">
        {isLoading ? (
          <div className="rounded-lg border border-line bg-white p-5">
            <Spinner />
          </div>
        ) : null}
        {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div> : null}
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        {!isLoading && analytics ? (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-line bg-white p-4">
                <div className="text-xs uppercase text-muted">{t("Status")}</div>
                <div className="mt-2">
                  <Badge tone={statusTone(capture.status)}>{t(capture.status)}</Badge>
                </div>
              </div>
              <div className="rounded-lg border border-line bg-white p-4">
                <div className="text-xs uppercase text-muted">{t("Total flows")}</div>
                <div className="mt-1 text-2xl font-semibold text-ink">{summary.total_flows}</div>
              </div>
              <div className="rounded-lg border border-line bg-white p-4">
                <div className="text-xs uppercase text-muted">{t("Anomalies")}</div>
                <div className="mt-1 text-2xl font-semibold text-ink">{summary.anomaly_flows}</div>
              </div>
              <div className="rounded-lg border border-line bg-white p-4">
                <div className="text-xs uppercase text-muted">{t("Anomaly rate")}</div>
                <div className="mt-1 text-2xl font-semibold text-ink">{formatPercent(summary.anomaly_rate)}</div>
              </div>
            </div>

            {capture.error_message ? (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{capture.error_message}</div>
            ) : null}

            <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
              <div className="rounded-lg border border-line bg-white p-4">
                <h2 className="text-base font-semibold text-ink">{t("Score distribution")}</h2>
                <div className="mt-4 h-72">
                  {scoreBuckets.length ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={scoreBuckets} margin={{ top: 8, right: 10, left: 0, bottom: 44 }}>
                        <CartesianGrid stroke="#d9dee7" strokeDasharray="3 3" />
                        <XAxis dataKey="range" angle={-35} textAnchor="end" height={70} tick={{ fontSize: 11 }} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#0f766e" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center text-sm text-muted">{t("No distribution data.")}</div>
                  )}
                </div>
              </div>

              <div className="grid gap-5">
                <EndpointTable title={t("Top sources")} rows={analytics.top_sources} t={t} />
                <EndpointTable title={t("Top destinations")} rows={analytics.top_destinations} t={t} />
              </div>
            </div>

            <div className="overflow-hidden rounded-lg border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h2 className="text-base font-semibold text-ink">{t("Recent anomaly flows")}</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[920px] text-left text-sm">
                  <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-3 font-semibold">{t("Timestamp")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Endpoint")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Protocol")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Packets")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Bytes")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Score")}</th>
                      <th className="px-4 py-3 font-semibold">{t("Prediction")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {analytics.recent_flows.map((flow) => (
                      <tr key={flow.id} className="cursor-pointer hover:bg-panel" onClick={() => openFlowDetail(flow)}>
                        <td className="px-4 py-3 text-muted">{formatDateTime(flow.flow_timestamp)}</td>
                        <td className="px-4 py-3 font-medium text-ink">{endpointLabel(flow)}</td>
                        <td className="px-4 py-3 text-muted">{flow.protocol ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{flow.bidirectional_packets ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{flow.bidirectional_bytes ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{formatScore(flow.anomaly_score)}</td>
                        <td className="px-4 py-3">
                          <Badge tone={flow.prediction === 1 ? "red" : "neutral"}>{flow.prediction === 1 ? "ANOMALY" : "BENIGN"}</Badge>
                        </td>
                      </tr>
                    ))}
                    {analytics.recent_flows.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan="7">
                          {t("No anomaly flows yet.")}
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : null}
      </section>
      {(selectedFlowDetail || isFlowDetailLoading || flowDetailError) && (
        <FlowDetailModal
          detail={selectedFlowDetail}
          error={flowDetailError}
          isLoading={isFlowDetailLoading}
          onClose={() => {
            setSelectedFlowDetail(null);
            setFlowDetailError("");
          }}
        />
      )}
    </>
  );
}

function EndpointTable({ title, rows, t }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
          <tr>
            <th className="px-4 py-3 font-semibold">{t("Value")}</th>
            <th className="px-4 py-3 text-right font-semibold">{t("Count")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row) => (
            <tr key={row.value}>
              <td className="px-4 py-3 font-medium text-ink">{row.value}</td>
              <td className="px-4 py-3 text-right text-muted">{row.count}</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td className="px-4 py-6 text-muted" colSpan="2">
                {t("No data.")}
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
