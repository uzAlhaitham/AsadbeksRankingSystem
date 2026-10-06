from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from .constants import USER_AGENT


class ImageLoader(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        try:
            self.nam.setTransferTimeout(10000)  # 10 sekund
        except Exception:
            pass
        self.cache = {}
        self.pending = {}
        self._failed = set()

    def load(self, url, callback):
        if not url:
            self._safe(callback, None); return
        urls = url if isinstance(url, list) else [url]
        key = urls[0]

        if key in self.cache:
            self._safe(callback, self.cache[key]); return
        if key in self._failed:
            self._safe(callback, None); return
        if key in self.pending:
            self.pending[key].append(callback); return

        print(f"[Img] LOAD {key}")
        self.pending[key] = [callback]
        self._try(0, urls, key)

    def _try(self, idx, urls, key):
        if idx >= len(urls):
            self._failed.add(key)
            print(f"[Img] FAIL {key}")
            cbs = self.pending.pop(key, [])
            for cb in cbs: self._safe(cb, None)
            return
        req = QNetworkRequest(QUrl(urls[idx]))
        req.setRawHeader(b"User-Agent", USER_AGENT.encode())
        reply = self.nam.get(req)
        reply.finished.connect(lambda r=reply, i=idx, u=urls, k=key: self._done(i, u, k, r))

    def _done(self, idx, urls, key, reply):
        data = bytes(reply.readAll())
        http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        reply.deleteLater()
        pm = QPixmap()
        if http and http < 400:
            pm.loadFromData(data)
        if not pm.isNull():
            print(f"[Img] OK {urls[idx]} ({len(data)}b)")
            self.cache[key] = pm
            cbs = self.pending.pop(key, [])
            for cb in cbs: self._safe(cb, pm)
            return
        self._try(idx + 1, urls, key)

    @staticmethod
    def _safe(cb, arg):
        try: cb(arg)
        except RuntimeError: pass
