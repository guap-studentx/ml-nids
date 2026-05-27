class AppError(Exception):
    status_code = 400
    detail = "Application error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class AuthError(AppError):
    status_code = 401
    detail = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = 403
    detail = "Permission denied"


class ModelNotFoundError(AppError):
    status_code = 404
    detail = "Model not found"


class ModelConflictError(AppError):
    status_code = 409
    detail = "Model cannot be deleted"


class CaptureNotFoundError(AppError):
    status_code = 404
    detail = "Capture session not found"


class LiveSessionNotFoundError(AppError):
    status_code = 404
    detail = "Live session not found"


class ExportNotFoundError(AppError):
    status_code = 404
    detail = "Capture export file not found"


class FlowNotFoundError(AppError):
    status_code = 404
    detail = "Flow not found"


class ReportNotFoundError(AppError):
    status_code = 404
    detail = "Report not found"


class AgentNotFoundError(AppError):
    status_code = 404
    detail = "Agent not found"


class AgentOfflineError(AppError):
    status_code = 409
    detail = "Agent is offline"


class AgentCaptureError(AppError):
    status_code = 409
    detail = "Capture is not assigned to this agent"


class InvalidArtifactError(AppError):
    status_code = 400
    detail = "Invalid model artifact"
