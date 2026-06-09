import { Download, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { downloadReport, listReports } from "../api/reports";
import Badge from "../components/Badge";
import Button from "../components/Button";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import { useLanguage } from "../context/LanguageContext";

export default function Reports() {
  const { t } = useLanguage();
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState("");

  const loadReports = useCallback(async () => {
    setError("");
    setIsLoading(true);
    try {
      const response = await listReports();
      setReports(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  async function handleDownload(report) {
    setError("");
    setDownloadingId(report.id);
    try {
      const blob = await downloadReport(report.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ml-nids-report-${report.id}.${report.format}`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDownloadingId("");
    }
  }

  return (
    <>
      <PageHeader
        title={t("Reports")}
        description={t("Generated analysis reports. Total: {total}.", { total })}
        actions={
          <Button onClick={loadReports}>
            <RefreshCw size={16} />
            {t("Refresh")}
          </Button>
        }
      />
      <section className="grid gap-5 p-5">
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
                    <th className="px-4 py-3 font-semibold">{t("Report")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Capture")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Format")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Status")}</th>
                    <th className="px-4 py-3 font-semibold">{t("Created")}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t("Actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {reports.map((report) => (
                    <tr key={report.id} className="hover:bg-panel">
                      <td className="px-4 py-3 font-medium text-ink">{report.id}</td>
                      <td className="px-4 py-3 text-muted">{report.session_id}</td>
                      <td className="px-4 py-3 text-muted">{report.format.toUpperCase()}</td>
                      <td className="px-4 py-3">
                        <Badge tone="green">{t(report.status)}</Badge>
                      </td>
                      <td className="px-4 py-3 text-muted">{new Date(report.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end">
                          <Button disabled={downloadingId === report.id} onClick={() => handleDownload(report)}>
                            <Download size={16} />
                            {t("Download")}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {reports.length === 0 ? (
                    <tr>
                      <td className="px-4 py-6 text-muted" colSpan="6">
                        {t("No reports yet.")}
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
