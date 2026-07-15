"""统一异常类层次。"""


class XingjiException(Exception):
    """应用基础异常，所有业务异常继承此类。"""

    http_status_code: int = 500
    error_code: int = 50000
    message: str = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class AgentException(XingjiException):
    """Agent 层处理错误。"""

    http_status_code = 500
    error_code = 50001
    message = "Agent processing error"


class ValidationException(XingjiException):
    """用户输入校验失败。"""

    http_status_code = 400
    error_code = 40000
    message = "Validation error"


class ExternalServiceException(XingjiException):
    """外部服务调用失败（LLM API 等）。"""

    http_status_code = 502
    error_code = 50200
    message = "External service error"
