import json
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

USER_AGENT_BROWSER = (
    b"Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
)


class AkashaClient(QObject):
    ranks_ready = Signal(dict)
    debug = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nam = QNetworkAccessManager(self)
        self._active_replies = set()

    def fetch_ranks(self, uid):
        url = f"https://akasha.cv/api/getCalculationsForUser/{uid}?_t={id(self)}"
        self.debug.emit(f"try {url}")
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", USER_AGENT_BROWSER)
        req.setRawHeader(b"Accept", b"application/json, text/plain, */*")
        req.setRawHeader(b"Referer", b"https://akasha.cv/")
        req.setRawHeader(b"Origin", b"https://akasha.cv")
        req.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        reply = self.nam.get(req)
        self._active_replies.add(reply)
        reply.finished.connect(lambda r=reply, u=uid: self._on_reply(r, u))

    def _on_reply(self, reply, uid):
        if reply not in self._active_replies:
            reply.deleteLater()
            return
        self._active_replies.discard(reply)

        err = reply.error()
        http = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        data = bytes(reply.readAll())
        reply.deleteLater()

        self.debug.emit(f"  HTTP {http}, {len(data)}b")

        if err != QNetworkReply.NetworkError.NoError or (http and http >= 400):
            self.debug.emit(f"  FAIL {err}")
            self.ranks_ready.emit({})
            return

        try:
            obj = json.loads(data.decode("utf-8", "replace"))
        except Exception as e:
            self.debug.emit(f"  parse FAIL {e}")
            self.ranks_ready.emit({})
            return

        arr = obj.get("data", obj) if isinstance(obj, dict) else obj
        if not isinstance(arr, list):
            self.debug.emit(f"  not list: {type(arr)}")
            self.ranks_ready.emit({})
            return

        ranks = self._parse(arr)
        self.debug.emit(f"  parsed {len(ranks)}")
        self.ranks_ready.emit(ranks)

    def _parse(self, data):
        out = {}
        for uc in data:
            if not isinstance(uc, dict):
                continue
            aid = uc.get("characterId")
            if not aid:
                continue
            calcs = uc.get("calculations") or {}
            if isinstance(calcs, dict):
                calcs = list(calcs.values())
            if not isinstance(calcs, list) or not calcs:
                continue
            best = None
            for calc in calcs:
                if not isinstance(calc, dict):
                    continue
                ranking = calc.get("ranking")
                out_of = calc.get("outOf") or calc.get("out_of")
                if not ranking or not out_of:
                    continue
                percent = ranking / out_of
                # combo short nomi: "QB COMBO", "SPREAD", "VAPE" ...
                short = calc.get("short") or calc.get("name") or "Ranked"
                full_name = calc.get("name") or short
                if best is None or percent < best["percent"]:
                    best = {
                        "top": int(ranking),
                        "total": int(out_of),
                        "type": str(short),
                        "full_name": str(full_name),
                        "percent": percent,
                    }
            if best:
                out[str(aid)] = {
                    "top": best["top"],
                    "total": best["total"],
                    "type": best["type"],
                    "full_name": best["full_name"],
                    "percent": best["percent"],
                }
        return out
