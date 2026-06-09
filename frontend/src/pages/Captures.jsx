import { Play, RefreshCw, Square, Trash2, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listAgents } from "../api/agents";
import { deleteCapture, listCaptures, startLiveCapture, stopCapture, uploadCsvCapture, uploadPcapCapture } from "../api/captures";
import { listModels } from "../api/models";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

export default function Captures() {
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [captures, setCaptures] = useState([]);
  const [models, setModels] = useState([]);
  const [agents, setAgents] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isStartingLive, setIsStartingLive] = useState(false);
  const [deletingId, setDeletingId] = useState("");
  const [stoppingId, setStoppingId] = useState("");
  const [csvForm, setCsvForm] = useState({ name: "", modelId: "", file: null });
  const [pcapForm, setPcapForm] = useState({ name: "", modelId: "", file: null });
  const [liveForm, setLiveForm] = useState({
    name: "",
    modelId: "",
    agentId: "",
    iface: "",
    bpfFilter: "",
    durationSeconds: 30,
  });

  const loadCaptures = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      const response = await listCaptures();
      setCaptures(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCaptures();
    Promise.all([listModels(), listAgents()])
      .then(([items, agentItems]) => {
        const activeModels = items.filter((item) => item.is_active);
        const defaultModelId = activeModels.find((item) => item.is_default)?.id ?? activeModels[0]?.id ?? "";
        const onlineAgents = agentItems.filter((agent) => agent.status === "online");
        const defaultAgent = onlineAgents[0];
        const defaultIface = defaultAgent?.available_ifaces?.[0] ?? "";
        setModels(activeModels);
        setAgents(agentItems);
        setCsvForm((current) => ({ ...current, modelId: defaultModelId }));
        setPcapForm((current) => ({ ...current, modelId: defaultModelId }));
        setLiveForm((current) => ({
          ...current,
          modelId: defaultModelId,
          agentId: defaultAgent?.id ?? "",
          iface: defaultIface,
        }));
      })
      .catch((requestError) => setError(requestError.message));
  }, [loadCaptures]);

  useEffect(() => {
    const hasActiveCapture = captures.some((capture) => ["pending", "running", "stopping"].includes(capture.status));
    if (!hasActiveCapture) {
      return undefined;
    }

    const intervalId = window.setInterval(loadCaptures, 3000);
    return () => window.clearInterval(intervalId);
  }, [captures, loadCaptures]);

  async function handleUpload(event, form, uploadFn, label, resetForm) {
    event.preventDefault();
    if (!form.file || !form.modelId) {
      setError(t("Select a {label} file and a model", { label }));
      return;
    }

    setError("");
    setNotice("");
    setIsUploading(true);
    try {
      const response = await uploadFn({ file: form.file, modelId: form.modelId, name: form.name });
      setNotice(t("{label} analysis started. Session ID: {id}", { label: label.toUpperCase(), id: response.session_id }));
      resetForm();
      event.target.reset();
      await loadCaptures();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleStartLive(event) {
    event.preventDefault();
    if (!liveForm.modelId || !liveForm.agentId || !liveForm.iface) {
      setError(t("Select a model, online agent, and interface"));
      return;
    }

    setError("");
    setNotice("");
    setIsStartingLive(true);
    try {
      const response = await startLiveCapture({
        name: liveForm.name,
        modelId: liveForm.modelId,
        agentId: liveForm.agentId,
        iface: liveForm.iface,
        bpfFilter: liveForm.bpfFilter,
        durationSeconds: liveForm.durationSeconds,
      });
      setNotice(t("Live capture queued. Session ID: {id}", { id: response.session_id }));
      setLiveForm((current) => ({ ...current, name: "", bpfFilter: "" }));
      await loadCaptures();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsStartingLive(false);
    }
  }

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

  async function handleDeleteCapture(event, capture) {
    event.stopPropagation();
    setError("");
    setNotice("");
    setDeletingId(capture.id);
    try {
      await deleteCapture(capture.id);
      setNotice(t("Capture {name} deleted", { name: capture.name ?? capture.source_filename ?? capture.id }));
      await loadCaptures();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDeletingId("");
    }
  }

  async function handleStopCapture(event, capture) {
    event.stopPropagation();
    setError("");
    setNotice("");
    setStoppingId(capture.id);
    try {
      const response = await stopCapture(capture.id);
      setNotice(t("Stop requested for {name}. Status: {status}", { name: capture.name ?? capture.source_filename ?? capture.id, status: response.status }));
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
        title={t("Captures")}
        description={t("Offline and live analysis history. Total: {total}.", { total })}
        actions={
          <Button onClick={loadCaptures}>
            <RefreshCw size={16} />
            {t("Refresh")}
          </Button>
        }
      />
      <section className="grid gap-5 p-5">
        <div className="grid gap-5 2xl:grid-cols-2">
          <LiveCaptureForm
            form={liveForm}
            models={models}
            agents={agents}
            isStarting={isStartingLive}
            onChange={setLiveForm}
            onSubmit={handleStartLive}
            t={t}
          />
          <UploadForm
            title={t("Offline CSV analysis")}
            description={t("Upload an NFStream-format flow table for inference with the selected model.")}
            accept=".csv,text/csv"
            fileLabel="CSV"
            placeholder={t("For example, lab-portscan-xgboost")}
            form={csvForm}
            models={models}
            isUploading={isUploading}
            onChange={setCsvForm}
            t={t}
            onSubmit={(event) =>
              handleUpload(event, csvForm, uploadCsvCapture, "csv", () =>
                setCsvForm((current) => ({ name: "", modelId: current.modelId, file: null })),
              )
            }
          />
          <UploadForm
            title={t("Offline PCAP analysis")}
            description={t("Upload PCAP/PCAPNG: backend extracts flows through NFStream using research settings.")}
            accept=".pcap,.pcapng,application/vnd.tcpdump.pcap"
            fileLabel="PCAP"
            placeholder={t("For example, attack-window-01")}
            form={pcapForm}
            models={models}
            isUploading={isUploading}
            onChange={setPcapForm}
            t={t}
            onSubmit={(event) =>
              handleUpload(event, pcapForm, uploadPcapCapture, "pcap", () =>
                setPcapForm((current) => ({ name: "", modelId: current.modelId, file: null })),
              )
            }
          />
        </div>

        {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div> : null}
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        <div className="overflow-hidden rounded-lg border border-line bg-white">
          {isLoading ? (
            <div className="p-5">
              <Spinner />
            </div>
          ) : null}
          {!isLoading ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-left text-sm">
                <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("Name")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Mode")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Status")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Flows")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Anomalies")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Finished")}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t("Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {captures.map((capture) => (
                    <tr
                      key={capture.id}
                      className="cursor-pointer hover:bg-panel"
                      onClick={() => navigate(`/captures/${capture.id}`)}
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-ink">{capture.name ?? capture.source_filename ?? capture.id}</div>
                        {capture.error_message ? <div className="mt-1 text-xs text-danger">{capture.error_message}</div> : null}
                      </td>
                      <td className="px-4 py-3 text-muted">{t(capture.mode)}</td>
                      <td className="px-4 py-3">
                        <Badge tone={statusTone(capture.status)}>{t(capture.status)}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted">{capture.flows_total}</td>
                      <td className="px-4 py-3 text-muted">{capture.flows_anomaly}</td>
                      <td className="px-4 py-3 text-muted">{formatDateTime(capture.finished_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          {capture.mode === "live" && ["pending", "running", "stopping"].includes(capture.status) ? (
                            <Button disabled={stoppingId === capture.id || capture.status === "stopping"} onClick={(event) => handleStopCapture(event, capture)}>
                              <Square size={16} />
                              {t("Stop")}
                            </Button>
                          ) : null}
                          <Button
                            variant="danger"
                            disabled={deletingId === capture.id}
                            onClick={(event) => handleDeleteCapture(event, capture)}
                          >
                            <Trash2 size={16} />
                            {t("Delete")}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {captures.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan="7">
                        {t("No sessions yet.")}
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
}

function UploadForm({
  title,
  description,
  accept,
  fileLabel,
  placeholder,
  form,
  models,
  isUploading,
  onChange,
  onSubmit,
  t,
}) {
  function updateForm(values) {
    onChange((current) => ({ ...current, ...values }));
  }

  return (
    <form className="grid gap-4 rounded-lg border border-line bg-white p-4" onSubmit={onSubmit}>
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        <p className="text-sm text-muted">{description}</p>
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1.2fr_auto] lg:items-end">
        <Input label={t("Session name")} value={form.name} onChange={(event) => updateForm({ name: event.target.value })} placeholder={placeholder} />
        <label className="grid gap-1.5 text-sm text-ink">
          <span className="font-medium">{t("Model")}</span>
          <select
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
            value={form.modelId}
            onChange={(event) => updateForm({ modelId: event.target.value })}
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.display_name}
                {model.is_default ? ` · ${t("Default").toLowerCase()}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1.5 text-sm text-ink">
          <span className="font-medium">{fileLabel}</span>
          <input
            className="h-10 rounded-md border border-line bg-white px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-panel file:px-2 file:py-1 file:text-xs file:font-medium file:text-ink"
            type="file"
            accept={accept}
            onChange={(event) => updateForm({ file: event.target.files?.[0] ?? null })}
          />
        </label>
        <Button type="submit" variant="primary" disabled={isUploading || models.length === 0}>
          <Upload size={16} />
          {isUploading ? t("Uploading") : t("Upload")}
        </Button>
      </div>
    </form>
  );
}

function LiveCaptureForm({ form, models, agents, isStarting, onChange, onSubmit, t }) {
  const onlineAgents = agents.filter((agent) => agent.status === "online");
  const selectedAgent = agents.find((agent) => agent.id === form.agentId);
  const ifaces = selectedAgent?.available_ifaces ?? [];

  function updateForm(values) {
    onChange((current) => ({ ...current, ...values }));
  }

  function handleAgentChange(agentId) {
    const agent = agents.find((item) => item.id === agentId);
    updateForm({ agentId, iface: agent?.available_ifaces?.[0] ?? "" });
  }

  return (
    <form className="grid gap-4 rounded-lg border border-line bg-white p-4 2xl:col-span-2" onSubmit={onSubmit}>
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold text-ink">{t("Live capture")}</h2>
        <p className="text-sm text-muted">{t("Command to an online agent: capture traffic on a selected interface and analyze it with a model.")}</p>
      </div>
      <div className="grid gap-3 xl:grid-cols-[1.1fr_1fr_1fr_1fr_0.7fr_auto] xl:items-end">
        <Input
          label={t("Session name")}
          value={form.name}
          onChange={(event) => updateForm({ name: event.target.value })}
          placeholder={t("For example, live-office-traffic")}
        />
        <label className="grid gap-1.5 text-sm text-ink">
          <span className="font-medium">{t("Model")}</span>
          <select
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
            value={form.modelId}
            onChange={(event) => updateForm({ modelId: event.target.value })}
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.display_name}
                {model.is_default ? ` · ${t("Default").toLowerCase()}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1.5 text-sm text-ink">
          <span className="font-medium">{t("Agent")}</span>
          <select
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
            value={form.agentId}
            onChange={(event) => handleAgentChange(event.target.value)}
          >
            {onlineAgents.length === 0 ? <option value="">{t("No online agents")}</option> : null}
            {onlineAgents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1.5 text-sm text-ink">
          <span className="font-medium">{t("Interface")}</span>
          <select
            className="h-10 rounded-md border border-line bg-white px-3 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-teal-100"
            value={form.iface}
            onChange={(event) => updateForm({ iface: event.target.value })}
          >
            {ifaces.length === 0 ? <option value="">{t("No interfaces")}</option> : null}
            {ifaces.map((iface) => (
              <option key={iface} value={iface}>
                {iface}
              </option>
            ))}
          </select>
        </label>
        <Input
          label={t("Duration, sec")}
          type="number"
          min="1"
          max="3600"
          value={form.durationSeconds}
          onChange={(event) => updateForm({ durationSeconds: event.target.value })}
        />
        <Button type="submit" variant="primary" disabled={isStarting || models.length === 0 || !form.agentId || !form.iface}>
          <Play size={16} />
          {isStarting ? t("Starting") : t("Start")}
        </Button>
      </div>
      <Input
        label={t("BPF filter")}
        value={form.bpfFilter}
        onChange={(event) => updateForm({ bpfFilter: event.target.value })}
        placeholder={t("For example, tcp port 443")}
      />
    </form>
  );
}
