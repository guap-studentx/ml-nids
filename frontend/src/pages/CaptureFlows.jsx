import { ArrowLeft, ChevronLeft, ChevronRight, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getFlowDetail, listFlows } from "../api/captures";
import Badge from "../components/Badge";
import Button from "../components/Button";
import FlowDetailModal from "../components/FlowDetailModal";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";

const pageSize = 50;

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

export default function CaptureFlows() {
  const { captureId } = useParams();
  const [flows, setFlows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [selectedFlowDetail, setSelectedFlowDetail] = useState(null);
  const [flowDetailError, setFlowDetailError] = useState("");
  const [isFlowDetailLoading, setIsFlowDetailLoading] = useState(false);
  const [draftFilters, setDraftFilters] = useState({
    prediction: "",
    min_score: "",
    src_ip: "",
    dst_ip: "",
    protocol: "",
  });
  const [appliedFilters, setAppliedFilters] = useState({
    prediction: "",
    min_score: "",
    src_ip: "",
    dst_ip: "",
    protocol: "",
  });

  const page = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const params = useMemo(
    () => ({
      ...appliedFilters,
      limit: pageSize,
      offset,
    }),
    [appliedFilters, offset],
  );

  const loadFlows = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      const response = await listFlows(captureId, params);
      setFlows(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, [captureId, params]);

  useEffect(() => {
    loadFlows();
  }, [loadFlows]);

  function handleFilterChange(key, value) {
    setDraftFilters((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    setAppliedFilters(draftFilters);
    setOffset(0);
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

  return (
    <>
      <PageHeader
        title="Capture flows"
        description={`${captureId} · ${total} записей`}
        actions={
          <>
            <Link to={`/captures/${captureId}`}>
              <Button>
                <ArrowLeft size={16} />
                Back
              </Button>
            </Link>
            <Button onClick={loadFlows}>
              <RefreshCw size={16} />
              Refresh
            </Button>
          </>
        }
      />

      <section className="grid gap-5 p-5">
        <form className="rounded-lg border border-line bg-white p-4" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[160px_160px_1fr_1fr_140px_auto] xl:items-end">
            <label className="grid gap-1.5 text-sm text-ink">
              <span className="font-medium">Prediction</span>
              <select
                className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
                value={draftFilters.prediction}
                onChange={(event) => handleFilterChange("prediction", event.target.value)}
              >
                <option value="">All</option>
                <option value="1">Anomaly</option>
                <option value="0">Benign</option>
              </select>
            </label>
            <Input
              label="Min score"
              type="number"
              min="0"
              step="0.0001"
              value={draftFilters.min_score}
              onChange={(event) => handleFilterChange("min_score", event.target.value)}
            />
            <Input label="Source IP" value={draftFilters.src_ip} onChange={(event) => handleFilterChange("src_ip", event.target.value)} />
            <Input label="Destination IP" value={draftFilters.dst_ip} onChange={(event) => handleFilterChange("dst_ip", event.target.value)} />
            <Input
              label="Protocol"
              type="number"
              min="0"
              max="255"
              value={draftFilters.protocol}
              onChange={(event) => handleFilterChange("protocol", event.target.value)}
            />
            <Button type="submit" variant="primary">
              <Search size={16} />
              Apply
            </Button>
          </div>
        </form>

        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        <div className="overflow-hidden rounded-lg border border-line bg-white">
          {isLoading ? (
            <div className="p-5">
              <Spinner />
            </div>
          ) : null}
          {!isLoading ? (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[1120px] text-left text-sm">
                  <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Timestamp</th>
                      <th className="px-4 py-3 font-semibold">Endpoint</th>
                      <th className="px-4 py-3 font-semibold">Protocol</th>
                      <th className="px-4 py-3 font-semibold">Duration ms</th>
                      <th className="px-4 py-3 font-semibold">Packets</th>
                      <th className="px-4 py-3 font-semibold">Bytes</th>
                      <th className="px-4 py-3 font-semibold">Score</th>
                      <th className="px-4 py-3 font-semibold">Prediction</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {flows.map((flow) => (
                      <tr key={flow.id} className="cursor-pointer hover:bg-panel" onClick={() => openFlowDetail(flow)}>
                        <td className="px-4 py-3 text-muted">{formatDateTime(flow.flow_timestamp)}</td>
                        <td className="px-4 py-3 font-medium text-ink">{endpointLabel(flow)}</td>
                        <td className="px-4 py-3 text-muted">{flow.protocol ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{flow.bidirectional_duration_ms ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{flow.bidirectional_packets ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{flow.bidirectional_bytes ?? "-"}</td>
                        <td className="px-4 py-3 text-muted">{formatScore(flow.anomaly_score)}</td>
                        <td className="px-4 py-3">
                          <Badge tone={flow.prediction === 1 ? "red" : "neutral"}>{flow.prediction === 1 ? "ANOMALY" : "BENIGN"}</Badge>
                        </td>
                      </tr>
                    ))}
                    {flows.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan="8">
                          Flow не найдены.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-col gap-3 border-t border-line px-4 py-3 text-sm text-muted md:flex-row md:items-center md:justify-between">
                <div>
                  Page {page} of {totalPages}
                </div>
                <div className="flex gap-2">
                  <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>
                    <ChevronLeft size={16} />
                    Previous
                  </Button>
                  <Button disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>
                    Next
                    <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
            </>
          ) : null}
        </div>
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
