import { Plus, RadioTower, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { createAgent, deleteAgent, getAgentIfaces, listAgents } from "../api/agents";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";

function statusTone(status) {
  if (status === "online") return "green";
  if (status === "busy") return "blue";
  if (status === "offline") return "neutral";
  return "amber";
}

function formatTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export default function Agents() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [agents, setAgents] = useState([]);
  const [name, setName] = useState("");
  const [createdToken, setCreatedToken] = useState(null);
  const [ifacesByAgent, setIfacesByAgent] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const isAdmin = user?.role === "admin";

  const loadAgents = useCallback(async ({ silent = false } = {}) => {
    setError("");
    if (!silent) {
      setIsLoading(true);
    }
    try {
      setAgents(await listAgents());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadAgents();
    const intervalId = window.setInterval(() => {
      loadAgents({ silent: true });
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [loadAgents]);

  async function handleCreate(event) {
    event.preventDefault();
    if (!name.trim()) {
      setError(t("Enter agent name"));
      return;
    }

    setError("");
    setNotice("");
    setIsCreating(true);
    try {
      const response = await createAgent(name.trim());
      setCreatedToken({ name: response.name, token: response.agent_token });
      setNotice(t("Agent created. Token is shown only once."));
      setName("");
      await loadAgents();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDelete(agent) {
    setBusyId(agent.id);
    setError("");
    setNotice("");
    try {
      await deleteAgent(agent.id);
      setNotice(t("Agent {name} deleted", { name: agent.name }));
      await loadAgents();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyId("");
    }
  }

  async function handleIfaces(agent) {
    setBusyId(agent.id);
    setError("");
    try {
      const response = await getAgentIfaces(agent.id);
      setIfacesByAgent((current) => ({ ...current, [agent.id]: response.ifaces }));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyId("");
    }
  }

  return (
    <>
      <PageHeader
        title={t("Agents")}
        description={t("Manage livecap-agent sensors: registration, interfaces, and connection state.")}
        actions={
          <Button onClick={loadAgents}>
            <RefreshCw size={16} />
            {t("Refresh")}
          </Button>
        }
      />
      <section className="grid gap-5 p-5">
        {!isAdmin ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
            {t("Agent management is available only to administrators.")}
          </div>
        ) : null}

        <form className="grid gap-4 rounded-lg border border-line bg-white p-4" onSubmit={handleCreate}>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal-50 text-accent">
              <RadioTower size={18} />
            </div>
            <div>
              <h2 className="text-base font-semibold text-ink">{t("Add livecap-agent")}</h2>
              <p className="text-sm text-muted">{t("Create an agent record and save the token for running it on the sensor host.")}</p>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
            <Input label={t("Agent name")} value={name} onChange={(event) => setName(event.target.value)} placeholder="ubuntu-sensor-01" />
            <Button type="submit" variant="primary" disabled={!isAdmin || isCreating}>
              <Plus size={16} />
              {isCreating ? t("Creating") : t("Create")}
            </Button>
          </div>
        </form>

        {createdToken ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <div className="text-sm font-semibold text-emerald-800">{t("Token for {name}", { name: createdToken.name })}</div>
            <div className="mt-2 break-all rounded-md border border-emerald-200 bg-white px-3 py-2 font-mono text-sm text-ink">
              {createdToken.token}
            </div>
          </div>
        ) : null}
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
              <table className="w-full min-w-[920px] text-left text-sm">
                <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-3 font-semibold">{t("Name")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Status")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Last seen")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Interfaces")}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t("Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {agents.map((agent) => {
                    const visibleIfaces = ifacesByAgent[agent.id] ?? agent.available_ifaces ?? [];
                    return (
                      <tr key={agent.id} className="hover:bg-panel">
                        <td className="px-4 py-3">
                          <div className="font-medium text-ink">{agent.name}</div>
                          <div className="text-xs text-muted">{agent.id}</div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={statusTone(agent.status)}>{t(agent.status ?? "unknown")}</Badge>
                        </td>
                        <td className="px-4 py-3 text-muted">{formatTime(agent.last_seen_at)}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            {visibleIfaces.map((iface) => (
                              <Badge key={iface}>{iface}</Badge>
                            ))}
                            {visibleIfaces.length === 0 ? <span className="text-muted">-</span> : null}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-2">
                            <Button disabled={!isAdmin || busyId === agent.id} onClick={() => handleIfaces(agent)}>
                              {t("Ifaces")}
                            </Button>
                            <Button variant="danger" disabled={!isAdmin || busyId === agent.id} onClick={() => handleDelete(agent)}>
                              <Trash2 size={16} />
                              {t("Delete")}
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {agents.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan="5">
                        {t("No agents yet.")}
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
