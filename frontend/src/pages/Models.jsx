import { Check, Eye, RefreshCw, Star, Trash2, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { deleteModel, getModel, listModels, updateModel, uploadModel } from "../api/models";
import Badge from "../components/Badge";
import Button from "../components/Button";
import Input from "../components/Input";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useAuth } from "../context/AuthContext";

function formatMetric(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return Number(value).toFixed(4);
}

function getF1(model) {
  return model.metrics_test?.f1_anomaly ?? model.metrics_test?.f1 ?? model.metrics_test?.f1_score;
}

export default function Models() {
  const { user } = useAuth();
  const [models, setModels] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [detailModel, setDetailModel] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({ modelId: "", displayName: "", file: null });

  const isAdmin = user?.role === "admin";
  const defaultModel = useMemo(() => models.find((model) => model.is_default), [models]);

  async function loadModels() {
    setError("");
    setIsLoading(true);
    try {
      setModels(await listModels());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadModels();
  }, []);

  async function handlePatch(model, payload, successMessage) {
    setBusyId(model.id);
    setError("");
    setNotice("");
    try {
      await updateModel(model.id, payload);
      setNotice(successMessage);
      await loadModels();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyId("");
    }
  }

  async function handleDelete(model) {
    setBusyId(model.id);
    setError("");
    setNotice("");
    try {
      await deleteModel(model.id);
      setNotice("Модель удалена");
      await loadModels();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusyId("");
    }
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!uploadForm.file) {
      setError("Выберите .joblib файл модели");
      return;
    }
    setError("");
    setNotice("");
    setIsUploading(true);
    try {
      const response = await uploadModel(uploadForm);
      setNotice(`Модель ${response.display_name} загружена`);
      setUploadForm({ modelId: "", displayName: "", file: null });
      event.target.reset();
      await loadModels();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDetails(model) {
    setError("");
    setIsDetailLoading(true);
    setDetailModel(model);
    try {
      setDetailModel(await getModel(model.id));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsDetailLoading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Models"
        description="Реестр обученных моделей, загруженных из артефактов исследовательской части."
        actions={
          <Button onClick={loadModels}>
            <RefreshCw size={16} />
            Refresh
          </Button>
        }
      />
      <section className="grid gap-4 p-5">
        <form className="grid gap-4 rounded-lg border border-line bg-white p-4" onSubmit={handleUpload}>
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold text-ink">Upload model artifact</h2>
            <p className="text-sm text-muted">Загрузка `.joblib` артефакта в формате исследовательского контракта.</p>
          </div>
          <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1.2fr_auto] lg:items-end">
            <Input
              label="Model ID"
              value={uploadForm.modelId}
              onChange={(event) => setUploadForm((current) => ({ ...current, modelId: event.target.value }))}
              placeholder="optional-custom-id"
            />
            <Input
              label="Display name"
              value={uploadForm.displayName}
              onChange={(event) => setUploadForm((current) => ({ ...current, displayName: event.target.value }))}
              placeholder="Optional display name"
            />
            <label className="grid gap-1.5 text-sm text-ink">
              <span className="font-medium">Artifact</span>
              <input
                className="h-10 rounded-md border border-line bg-white px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-panel file:px-2 file:py-1 file:text-xs file:font-medium file:text-ink"
                type="file"
                accept=".joblib"
                onChange={(event) => setUploadForm((current) => ({ ...current, file: event.target.files?.[0] ?? null }))}
              />
            </label>
            <Button type="submit" variant="primary" disabled={!isAdmin || isUploading}>
              <Upload size={16} />
              {isUploading ? "Uploading" : "Upload"}
            </Button>
          </div>
        </form>

        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-line bg-white p-4">
            <div className="text-xs uppercase text-muted">Registered</div>
            <div className="mt-1 text-2xl font-semibold text-ink">{models.length}</div>
          </div>
          <div className="rounded-lg border border-line bg-white p-4">
            <div className="text-xs uppercase text-muted">Active</div>
            <div className="mt-1 text-2xl font-semibold text-ink">{models.filter((model) => model.is_active).length}</div>
          </div>
          <div className="rounded-lg border border-line bg-white p-4">
            <div className="text-xs uppercase text-muted">Default</div>
            <div className="mt-1 truncate text-lg font-semibold text-ink">{defaultModel?.display_name ?? "-"}</div>
          </div>
        </div>

        {notice ? <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div> : null}
        {error ? <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-danger">{error}</div> : null}

        <div className="overflow-hidden rounded-lg border border-line bg-white">
          {isLoading ? <div className="p-5"><Spinner /></div> : null}
          {!isLoading ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[980px] text-left text-sm">
                <thead className="border-b border-line bg-panel text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Name</th>
                    <th className="px-4 py-3 font-semibold">Class</th>
                    <th className="px-4 py-3 font-semibold">Score</th>
                    <th className="px-4 py-3 font-semibold">Threshold</th>
                    <th className="px-4 py-3 font-semibold">F1 anomaly</th>
                    <th className="px-4 py-3 font-semibold">State</th>
                    <th className="px-4 py-3 text-right font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {models.map((model) => (
                    <tr key={model.id} className="hover:bg-panel">
                      <td className="px-4 py-3">
                        <div className="font-medium text-ink">{model.display_name}</div>
                        <div className="text-xs text-muted">{model.model_id}</div>
                      </td>
                      <td className="px-4 py-3 text-muted">{model.model_class_name}</td>
                      <td className="px-4 py-3 text-muted">{model.score_type}</td>
                      <td className="px-4 py-3 text-muted">{formatMetric(model.decision_threshold)}</td>
                      <td className="px-4 py-3 text-muted">{formatMetric(getF1(model))}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge tone={model.is_active ? "green" : "neutral"}>{model.is_active ? "active" : "inactive"}</Badge>
                          {model.is_default ? <Badge tone="blue">default</Badge> : null}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <Button disabled={busyId === model.id} onClick={() => handleDetails(model)}>
                            <Eye size={16} />
                            Details
                          </Button>
                          <Button
                            disabled={!isAdmin || busyId === model.id}
                            onClick={() => handlePatch(model, { is_active: !model.is_active }, "Статус модели обновлен")}
                          >
                            <Check size={16} />
                            {model.is_active ? "Disable" : "Enable"}
                          </Button>
                          <Button
                            disabled={!isAdmin || model.is_default || busyId === model.id}
                            onClick={() => handlePatch(model, { is_default: true }, "Default-модель обновлена")}
                          >
                            <Star size={16} />
                            Default
                          </Button>
                          <Button
                            variant="danger"
                            disabled={!isAdmin || model.is_default || busyId === model.id}
                            onClick={() => handleDelete(model)}
                          >
                            <Trash2 size={16} />
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </section>
      <ModelDetailsModal
        model={detailModel}
        isLoading={isDetailLoading}
        onClose={() => setDetailModel(null)}
      />
    </>
  );
}

function ModelDetailsModal({ model, isLoading, onClose }) {
  if (!model) return null;
  const metricEntries = Object.entries(model.metrics_test ?? {});
  const trainMetricEntries = Object.entries(model.metrics_train ?? {});
  const configEntries = Object.entries(model.architecture_config ?? {});
  const importances = model.feature_importance ?? [];

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="max-h-[88vh] w-full max-w-5xl overflow-hidden rounded-lg border border-line bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-ink">{model.display_name}</h2>
            <div className="mt-1 text-xs text-muted">{model.model_id} · {model.model_class_name}</div>
          </div>
          <Button onClick={onClose}>Close</Button>
        </div>
        <div className="max-h-[72vh] overflow-y-auto p-5">
          {isLoading ? <Spinner /> : null}
          {!isLoading ? (
            <div className="grid gap-5">
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Threshold" value={formatMetric(model.decision_threshold)} />
                <Metric label="Score type" value={model.score_type} />
                <Metric label="Features" value={model.features?.length ?? 0} />
                <Metric label="Size KB" value={formatMetric(model.size_kb)} />
              </div>

              <DetailSection title="Test metrics" entries={metricEntries} />
              {trainMetricEntries.length ? <DetailSection title="Train metrics" entries={trainMetricEntries} /> : null}
              {configEntries.length ? <DetailSection title="Model config" entries={configEntries} /> : null}

              <div className="rounded-lg border border-line">
                <div className="border-b border-line bg-panel px-4 py-3 text-sm font-semibold text-ink">Feature importance</div>
                <div className="grid gap-2 p-4">
                  {importances.map((item) => (
                    <div key={item.feature} className="grid gap-2 md:grid-cols-[220px_1fr_90px] md:items-center">
                      <div className="truncate text-sm text-ink">{item.feature}</div>
                      <div className="h-2 overflow-hidden rounded bg-panel">
                        <div
                          className="h-full bg-accent"
                          style={{ width: `${Math.min(100, Math.abs(item.importance) * 100)}%` }}
                        />
                      </div>
                      <div className="text-right text-sm text-muted">{formatMetric(item.importance)}</div>
                    </div>
                  ))}
                  {importances.length === 0 ? <div className="text-sm text-muted">Feature importance недоступен для этого артефакта.</div> : null}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-line bg-panel px-3 py-2">
      <div className="text-xs uppercase text-muted">{label}</div>
      <div className="mt-1 truncate text-base font-semibold text-ink">{value}</div>
    </div>
  );
}

function DetailSection({ title, entries }) {
  return (
    <div className="rounded-lg border border-line">
      <div className="border-b border-line bg-panel px-4 py-3 text-sm font-semibold text-ink">{title}</div>
      <div className="grid gap-0 divide-y divide-line">
        {entries.map(([key, value]) => (
          <div key={key} className="grid gap-2 px-4 py-2 text-sm md:grid-cols-[240px_1fr]">
            <div className="text-muted">{key}</div>
            <div className="break-words font-medium text-ink">
              {typeof value === "number" ? formatMetric(value) : JSON.stringify(value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
