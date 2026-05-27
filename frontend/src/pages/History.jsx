import { ChevronLeft, ChevronRight, Eye, RefreshCw, Search, Square, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteCapture, listCaptures, stopCapture } from "../api/captures";
import { listModels } from "../api/models";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";

const pageSize = 50;

function statusTone(status) {
  if (status === "completed") return "green";
  if (status === "failed") return "red";
  if (status === "running" || status === "stopping") return "blue";
  return "amber";
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime()) || date.getFullYear() <= 1971) return "-";
  return date.toLocaleString();
}

function toDateTimeParam(value, endOfDay = false) {
  if (!value) return "";
  return `${value}T${endOfDay ? "23:59:59" : "00:00:00"}`;
}

export default function History() {
  const navigate = useNavigate();
  const [captures, setCaptures] = useState([]);
  const [models, setModels] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState("");
  const [stoppingId, setStoppingId] = useState("");
  const [draftFilters, setDraftFilters] = useState({
    dateFrom: "",
    dateTo: "",
    mode: "",
    status: "",
    modelId: "",
  });
  const [appliedFilters, setAppliedFilters] = useState(draftFilters);

  const page = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const params = useMemo(
    () => ({
      mode: appliedFilters.mode,
      status: appliedFilters.status,
      model_id: appliedFilters.modelId,
      started_from: toDateTimeParam(appliedFilters.dateFrom),
      started_to: toDateTimeParam(appliedFilters.dateTo, true),
      limit: pageSize,
      offset,
    }),
    [appliedFilters, offset],
  );

  const loadCaptures = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      const response = await listCaptures(params);
      setCaptures(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, [params]);

  useEffect(() => {
    loadCaptures();
  }, [loadCaptures]);

  useEffect(() => {
    listModels()
      .then((items) => setModels(items.filter((item) => item.is_active)))
      .catch((requestError) => setError(requestError.message));
  }, []);

  function handleFilterChange(key, value) {
    setDraftFilters((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    setAppliedFilters(draftFilters);
    setOffset(0);
  }

  async function handleDelete(capture) {
    setError("");
    setNotice("");
    setDeletingId(capture.id);
    try {
      await deleteCapture(capture.id);
      setNotice(`Capture ${capture.name ?? capture.source_filename ?? capture.id} удален`);
      await loadCaptures();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDeletingId("");
    }
  }

  async function handleStop(capture) {
    setError("");
    setNotice("");
    setStoppingId(capture.id);
    try {
      const response = await stopCapture(capture.id);
      setNotice(`Stop requested for ${capture.name ?? capture.source_filename ?? capture.id}. Status: ${response.status}`);
      await loadCaptures();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setStoppingId("");
    }
  }

  return (
    <>
      <PageHeader
        title="History"
        description={`Архив capture-сессий с фильтрами. Всего: ${total}.`}
        actions={
          <Button onClick={loadCaptures}>
            <RefreshCw size={16} />
            Refresh
          </Button>
        }
      />
      <section className="grid gap-5 p-5">
        <form className="rounded-lg border border-line bg-white p-4" onSubmit={handleSubmit}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[150px_150px_170px_170px_1fr_auto] xl:items-end">
            <Input
              label="Date from"
              type="date"
              value={draftFilters.dateFrom}
              onChange={(event) => handleFilterChange("dateFrom", event.target.value)}
            />
            <Input
              label="Date to"
              type="date"
              value={draftFilters.dateTo}
              onChange={(event) => handleFilterChange("dateTo", event.target.value)}
            />
            <Select label="Mode" value={draftFilters.mode} onChange={(value) => handleFilterChange("mode", value)}>
              <option value="">All</option>
              <option value="offline_csv">Offline CSV</option>
              <option value="offline_pcap">Offline PCAP</option>
              <option value="live">Live</option>
            </Select>
            <Select label="Status" value={draftFilters.status} onChange={(value) => handleFilterChange("status", value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="stopping">Stopping</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="stopped">Stopped</option>
            </Select>
            <Select label="Model" value={draftFilters.modelId} onChange={(value) => handleFilterChange("modelId", value)}>
              <option value="">All</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.display_name}
                </option>
              ))}
            </Select>
            <Button type="submit" variant="primary">
              <Search size={16} />
              Apply
            </Button>
          </div>
        </form>

        {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div> : null}
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
                      <th className="px-4 py-3 font-semibold">Name</th>
                      <th className="px-4 py-3 font-semibold">Started</th>
                      <th className="px-4 py-3 font-semibold">Mode</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Flows</th>
                      <th className="px-4 py-3 font-semibold">Anomalies</th>
                      <th className="px-4 py-3 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {captures.map((capture) => (
                      <tr key={capture.id} className="hover:bg-panel">
                        <td className="px-4 py-3">
                          <div className="font-medium text-ink">{capture.name ?? capture.source_filename ?? capture.id}</div>
                          <div className="text-xs text-muted">{capture.id}</div>
                        </td>
                        <td className="px-4 py-3 text-muted">{formatDateTime(capture.started_at)}</td>
                        <td className="px-4 py-3 text-muted">{capture.mode}</td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(capture.status)}>{capture.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-muted">{capture.flows_total}</td>
                        <td className="px-4 py-3 text-muted">{capture.flows_anomaly}</td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-2">
                            <Button onClick={() => navigate(`/captures/${capture.id}`)}>
                              <Eye size={16} />
                              View
                            </Button>
                            {capture.mode === "live" && ["pending", "running", "stopping"].includes(capture.status) ? (
                              <Button disabled={stoppingId === capture.id || capture.status === "stopping"} onClick={() => handleStop(capture)}>
                                <Square size={16} />
                                Stop
                              </Button>
                            ) : null}
                            <Button variant="danger" disabled={deletingId === capture.id} onClick={() => handleDelete(capture)}>
                              <Trash2 size={16} />
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {captures.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-muted" colSpan="7">
                          Capture-сессий по выбранным фильтрам нет.
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
    </>
  );
}

function Select({ label, value, onChange, children }) {
  return (
    <label className="grid gap-1.5 text-sm text-ink">
      <span className="font-medium">{label}</span>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  );
}
