import json
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from .constants import USER_AGENT, GAMES


class EnkaClient(QObject):
    success = Signal(dict, str)
    failure = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on)
        self._uid = None

    def fetch(self, uid, game_key):
        self._uid = uid
        req = QNetworkRequest(QUrl(GAMES[game_key].format(uid=uid)))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        req.setRawHeader(b"Accept", b"application/json")
        req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                         QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self.nam.get(req)

    def _on(self, reply):
        uid = self._uid; self._uid = None
        http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll()).decode("utf-8", "replace")
        err = reply.error(); reply.deleteLater()

        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            msg = {400: "Invalid UID. Account does not exist.",
                   404: "Account not found.",
                   424: "Enka captcha required. Try again later.",
                   429: "Rate limited. Try again later."}.get(http, f"Request failed (HTTP {http}).")
            self.failure.emit(msg); return
        try:
            obj = json.loads(data)
        except Exception:
            self.failure.emit("Bad JSON from server."); return
        if not obj.get("playerInfo"):
            self.failure.emit("No account data in response."); return
        self.success.emit(obj, uid)
