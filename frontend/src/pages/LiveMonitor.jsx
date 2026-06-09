import { Eye, RefreshCw, Square, Trash2, Zap } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { listAgents } from "../api/agents";
import { createLiveSession, deleteLiveSession, listLiveSessionChunks, listLiveSessions, stopLiveSession } from "../api/liveSessions";
import { listModels } from "../api/models";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

function statusTone(status) {
  if (status === "completed" || status === "stopped") return "green";
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

function anomalyRate(session) {
  if (!session?.flows_total) return "0.0";
  return ((session.flows_anomaly / session.flows_total) * 100).toFixed(1);
}

export default function LiveMonitor() {
  const { t } = useLanguage();
  const [sessions, setSessions] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [models, setModels] = useState([]);
  const [agents, setAgents] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [stoppingId, setStoppingId] = useState("");
  const [deletingId, setDeletingId] = useState("");
  const [form, setForm] = useState({
    name: "",
    agentId: "",
    iface: "",
    modelId: "",
    bpfFilter: "",
    chunkSeconds: 15,
    durationSeconds: 3600,
  });

  const selectedSession = sessions.find((session) => session.id === selectedSessionId) ?? sessions[0];
  const onlineAgents = agents.filter((agent) => agent.status === "online");
  const selectedAgent = agents.find((agent) => agent.id === form.agentId);
  const ifaces = selectedAgent?.available_ifaces ?? [];
  const hasActiveSession = sessions.some((session) => ["pending", "running", "stopping"].includes(session.status));
  const timeline = useMemo(() => chunks.slice(-12), [chunks]);

  const loadSessions = useCallback(async ({ silent = false } = {}) => {
    setError("");
    if (!silent) setIsLoading(true);
    try {
      const response = await listLiveSessions({ limit: 50 });
      setSessions(response.items);
      setSelectedSessionId((current) => current || response.items[0]?.id || "");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (!silent) setIsLoading(false);
    }
  }, []);

  const loadChunks = useCallback(async (sessionId) => {
    if (!sessionId) {
      setChunks([]);
      return;
    }
    try {
      setChunks(await listLiveSessionChunks(sessionId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }, []);

  useEffect(() => {
    loadSessions();
    Promise.all([listModels(), listAgents()])
      .then(([modelItems, agentItems]) => {
        const activeModels = modelItems.filter((model) => model.is_active);
        const defaultModelId = activeModels.find((model) => model.is_default)?.id ?? activeModels[0]?.id ?? "";
        const defaultAgent = agentItems.find((agent) => agent.status === "online");
        setModels(activeModels);
        setAgents(agentItems);
        setForm((current) => ({
          ...current,
          modelId: defaultModelId,
          agentId: defaultAgent?.id ?? "",
          iface: defaultAgent?.available_ifaces?.[0] ?? "",
        }));
      })
      .catch((requestError) => setError(requestError.message));
  }, [loadSessions]);

  useEffect(() => {
    loadChunks(selectedSession?.id);
  }, [selectedSession?.id, loadChunks]);

  useEffect(() => {
    if (!hasActiveSession) return undefined;
    const intervalId = window.setInterval(async () => {
      await loadSessions({ silent: true });
      await loadChunks(selectedSession?.id);
    }, 3000);
    return () => window.clearInterval(intervalId);
  }, [hasActiveSession, loadChunks, loadSessions, selectedSession?.id]);

  function updateForm(values) {
    setForm((current) => ({ ...current, ...values }));
  }

  function handleAgentChange(agentId) {
    const agent = agents.find((item) => item.id === agentId);
    updateForm({ agentId, iface: agent?.available_ifaces?.[0] ?? "" });
  }

  async function handleStart(event) {
    event.preventDefault();
    if (!form.modelId || !form.agentId || !form.iface) {
      setError(t("Select a model, online agent, and interface"));
      return;
    }

    setError("");
    setNotice("");
    setIsStarting(true);
    try {
      const session = await createLiveSession({
        name: form.name,
        agentId: form.agentId,
        iface: form.iface,
        modelId: form.modelId,
        bpfFilter: form.bpfFilter,
        chunkSeconds: form.chunkSeconds,
        durationSeconds: form.durationSeconds,
      });
      setNotice(t("Live session created. ID: {id}", { id: session.id }));
      setSelectedSessionId(session.id);
      setForm((current) => ({ ...current, name: "", bpfFilter: "" }));
      await loadSessions({ silent: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsStarting(false);
    }
  }

  async function handleStop(session) {
    setError("");
    setNotice("");
    setStoppingId(session.id);
    try {
      const response = await stopLiveSession(session.id);
      setNotice(t("Stop requested for {name}. Status: {status}", { name: session.name || session.id, status: response.status }));
      await loadSessions({ silent: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setStoppingId("");
    }
  }

  async function handleDelete(session) {
    setError("");
    setNotice("");
    setDeletingId(session.id);
    try {
      await deleteLiveSession(session.id);
      setNotice(t("Live session {name} deleted", { name: session.name || session.id }));
      setChunks([]);
      setSelectedSessionId("");
      await loadSessions({ silent: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDeletingId("");
    }
  }

  return (
    <>
      <PageHeader
        title={t("Live Monitor")}
        description={t("Continuous traffic analysis: the agent sends short PCAP chunks, backend aggregates the result.")}
        actions={
          <Button onClick={() => loadSessions()}>
            <RefreshCw size={16} />
            {t("Refresh")}
          </Button>
        }
      />
      <section className="grid gap-5 p-5">
        <form className="grid gap-4 rounded-lg border border-line bg-white p-4" onSubmit={handleStart}>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal-50 text-accent">
              <Zap size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">{t("Start continuous session")}</h2>
              <p className="text-sm text-muted">{t("Rolling capture with configured chunk size and total duration.")}</p>
            </div>
          </div>
          <div className="grid gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr_0.7fr_0.7fr_auto] xl:items-end">
            <Input label={t("Name")} value={form.name} onChange={(event) => updateForm({ name: event.target.value })} placeholder="continuous-eth0" />
            <Select label={t("Model")} value={form.modelId} onChange={(event) => updateForm({ modelId: event.target.value })}>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.display_name}
                  {model.is_default ? ` · ${t("Default").toLowerCase()}` : ""}
                </option>
              ))}
            </Select>
            <Select label={t("Agent")} value={form.agentId} onChange={(event) => handleAgentChange(event.target.value)}>
              {onlineAgents.length === 0 ? <option value="">{t("No online agents")}</option> : null}
              {onlineAgents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </Select>
            <Select label={t("Interface")} value={form.iface} onChange={(event) => updateForm({ iface: event.target.value })}>
              {ifaces.length === 0 ? <option value="">{t("No interfaces")}</option> : null}
              {ifaces.map((iface) => (
                <option key={iface} value={iface}>
                  {iface}
                </option>
              ))}
            </Select>
            <Input
              label={t("Chunk, sec")}
              type="number"
              min="5"
              max="300"
              value={form.chunkSeconds}
              onChange={(event) => updateForm({ chunkSeconds: event.target.value })}
            />
            <Input
              label={t("Duration, sec")}
              type="number"
              min="30"
              max="21600"
              value={form.durationSeconds}
              onChange={(event) => updateForm({ durationSeconds: event.target.value })}
            />
            <Button type="submit" variant="primary" disabled={isStarting || !form.agentId || !form.iface || !form.modelId}>
              <Zap size={16} />
              {isStarting ? t("Starting") : t("Start")}
            </Button>
          </div>
          <Input label={t("BPF filter")} value={form.bpfFilter} onChange={(event) => updateForm({ bpfFilter: event.target.value })} placeholder="tcp port 443" />
        </form>

        {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div> : null}
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        {isLoading ? (
          <div className="rounded-lg border border-line bg-white p-5">
            <Spinner />
          </div>
        ) : null}

        {!isLoading ? (
          <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="overflow-hidden rounded-lg border border-line bg-white">
              <div className="border-b border-line px-4 py-3">
                <h2 className="text-base font-semibold text-ink">{t("Sessions")}</h2>
              </div>
              <div className="divide-y divide-line">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    type="button"
                    className={`grid w-full gap-2 px-4 py-3 text-left hover:bg-panel ${selectedSession?.id === session.id ? "bg-teal-50" : ""}`}
                    onClick={() => setSelectedSessionId(session.id)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0 truncate font-medium text-ink">{session.name || session.id}</div>
                      <Badge tone={statusTone(session.status)}>{t(session.status)}</Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs text-muted">
                      <span>{session.iface}</span>
                      <span>{session.flows_total} {t("Flows").toLowerCase()}</span>
                      <span>{session.flows_anomaly} {t("Anomalies").toLowerCase()}</span>
                    </div>
                  </button>
                ))}
                {sessions.length === 0 ? <div className="px-4 py-6 text-sm text-muted">{t("No live sessions yet.")}</div> : null}
              </div>
            </div>

            <div className="grid gap-5">
              <SessionSummary
                session={selectedSession}
                chunks={chunks}
                stoppingId={stoppingId}
                deletingId={deletingId}
                onStop={handleStop}
                onDelete={handleDelete}
                t={t}
              />
              <ChunkTimeline chunks={timeline} t={t} />
              <ChunksTable chunks={chunks} t={t} />
            </div>
          </div>
        ) : null}
      </section>
    </>
  );
}

function Select({ label, children, ...props }) {
  return (
    <label className="grid gap-1.5 text-sm text-ink">
      <span className="font-medium">{label}</span>
      <select
        className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

function SessionSummary({ session, chunks, stoppingId, deletingId, onStop, onDelete, t }) {
  if (!session) {
    return (
      <div className="rounded-lg border border-line bg-white p-4 text-sm text-muted">
        {t("Select or start a live session.")}
      </div>
    );
  }

  return (
    <div className="grid gap-4 rounded-lg border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">{session.name || "Live session"}</h2>
          <div className="mt-1 text-xs text-muted">{session.id}</div>
        </div>
        <div className="flex gap-2">
          <Badge tone={statusTone(session.status)}>{t(session.status)}</Badge>
          {["pending", "running", "stopping"].includes(session.status) ? (
            <Button disabled={stoppingId === session.id || session.status === "stopping"} onClick={() => onStop(session)}>
              <Square size={16} />
              {t("Stop")}
            </Button>
          ) : null}
          <Button variant="danger" disabled={deletingId === session.id} onClick={() => onDelete(session)}>
            <Trash2 size={16} />
            {t("Delete")}
          </Button>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-4">
        <Metric label={t("Flows")} value={session.flows_total} />
        <Metric label={t("Anomalies")} value={session.flows_anomaly} />
        <Metric label={t("Rate")} value={`${anomalyRate(session)}%`} />
        <Metric label={t("Chunks")} value={chunks.length} />
      </div>
      <div className="grid gap-2 text-sm text-muted sm:grid-cols-2">
        <div>{t("Interface")}: <span className="text-ink">{session.iface}</span></div>
        <div>{t("Chunk, sec")}: <span className="text-ink">{session.chunk_seconds}s</span></div>
        <div>{t("Started")}: <span className="text-ink">{formatDateTime(session.started_at)}</span></div>
        <div>{t("Finished")}: <span className="text-ink">{formatDateTime(session.finished_at)}</span></div>
      </div>
      {session.error_message ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{session.error_message}</div> : null}
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2">
      <div className="text-xs uppercase text-muted">{label}</div>
      <div className="mt-1 text-xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function ChunkTimeline({ chunks, t }) {
  const maxValue = Math.max(1, ...chunks.map((chunk) => chunk.flows_anomaly));
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <h2 className="text-base font-semibold text-ink">{t("Recent anomaly chunks")}</h2>
      <div className="mt-4 flex h-28 items-end gap-2">
        {chunks.map((chunk) => (
          <div key={chunk.id} className="flex min-w-8 flex-1 flex-col items-center gap-2">
            <div
              className="w-full rounded-t bg-accent"
              style={{ height: `${Math.max(6, (chunk.flows_anomaly / maxValue) * 96)}px` }}
              title={`${chunk.flows_anomaly} ${t("Anomalies").toLowerCase()}`}
            />
            <div className="text-[11px] text-muted">{chunk.chunk_index ?? "-"}</div>
          </div>
        ))}
        {chunks.length === 0 ? <div className="self-center text-sm text-muted">{t("No chunks yet.")}</div> : null}
      </div>
    </div>
  );
}

function ChunksTable({ chunks, t }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-white">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{t("Chunks")}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-3 font-semibold">#</th>
              <th className="px-4 py-3 font-semibold">{t("Status")}</th>
              <th className="px-4 py-3 font-semibold">{t("Flows")}</th>
              <th className="px-4 py-3 font-semibold">{t("Anomalies")}</th>
              <th className="px-4 py-3 font-semibold">{t("Finished")}</th>
              <th className="px-4 py-3 text-right font-semibold">{t("Open")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {chunks.map((chunk) => (
              <tr key={chunk.id} className="hover:bg-panel">
                <td className="px-4 py-3 text-ink">{chunk.chunk_index ?? "-"}</td>
                <td className="px-4 py-3"><Badge tone={statusTone(chunk.status)}>{t(chunk.status)}</Badge></td>
                <td className="px-4 py-3 text-muted">{chunk.flows_total}</td>
                <td className="px-4 py-3 text-muted">{chunk.flows_anomaly}</td>
                <td className="px-4 py-3 text-muted">{formatDateTime(chunk.finished_at)}</td>
                <td className="px-4 py-3 text-right">
                  <Link className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm font-medium text-ink hover:bg-panel" to={`/captures/${chunk.id}`}>
                    <Eye size={16} />
                    {t("Open")}
                  </Link>
                </td>
              </tr>
            ))}
            {chunks.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-muted" colSpan="6">
                  {t("No chunks yet. Start the agent so it can receive the command.")}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
