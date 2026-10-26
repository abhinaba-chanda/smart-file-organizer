"""The desktop window: pick a folder, preview, organize, undo, move duplicates aside. Built on tkinter/ttk only.

Start it with ``python -m smart_organizer.gui`` (or the ``organize-gui`` command / the Windows .exe).
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Callable, Optional

from . import gui_logic as logic

PAD = 16
CHECK_ON, CHECK_OFF = "\u2611", "\u2610"  # ballot boxes for the "include this file" column

# The app icon (folder with sorted file tabs), as small PNGs for the window/taskbar icon and the title row.
_APP_ICON = {
    16: "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABqUlEQVR42sWTvWuTQRzHP5dcIpKYYGNbkUp1kmDHLi4OLo7iKIL/gIiDq6uTm07OxVVHRXAQBLupFAvtUhEbrbQ1ad6e5rn7fR0e+jTxBdx68IW779vB8Ts46uUAzt9tXY7o0rhQNL3ceDz38b8K5m5vvHbSld+0PYn7Bdz+X5NWePvlyfyqB9AoKcxW91i6/pRKaXRgqQGPALrpMW49v8lW78T4za+Aqx7A0n3OVb7RrH/ODQ9PXaPlT+bnC3c6zIcBCNafVdhdK5UB3I0Vzba/dj/Viv3GwnQLGZjgQ+ksJrAIUsZlmhhuF0l2/U7tTP2iHyY0y1PVxsAqLA9mMCOHR5jBMGWMzzhVaXR+hqZPeoEgNxGMMTMuNhwSvGvrzwIDCxHf60FEE+EisDgN9xYKADwYRpY3I6MUFJWDYPheAhZFjFmropgqw0zRUfXZA54uGMeTSL9rWdiyAheET9oBM8AOm79HsbQJWz8CmHixmuahQ4AF4ZNukAuTwsH+zUqKokj7NqmZsllyktd2sh6ce6/g6hhYtLxgJwr0ryFWx7ni2pF/Rn4Bu004SMsvH0MAAAAASUVORK5CYII=",
    24: "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAACg0lEQVR42u2VP2gUQRTGf7N7d5qcYiTEhAjmkkCIQoRgIdqIlikEo40IIqZJI2pvZyVYCOK/Rgx2gtY2NgoSDQENgoXiXYgRD72YkNzlNrczz2L27ub+kZA60+y3b9983/dm3szCzthkqDI4dDM7AOFAfYJv1EYh7s1m7/bkty2QupHuMNrLAokWeWnPN2cy9/oz2xOYTKe0MulNcr8JvNoaqVpYeDTwoCLQM/k15RuVBrg6+oELRz5tSrK0nuT663PkCsmm372QgwtPh3/FACgWEd/CiaPv6Nv3ryY55+/lR6IbcWLtlDiZzzC9mKrECn881iLKkgkTALHyRwlDq6wDCDdqBG51jbPstzfaPAXDVM2IgZk7Haz/9SvtEwM4fmVobGUxjwi8bLtMUgIAjAAC2dwIItgKBIujdzEReRTrGo0TrHjs6kyO/X7GQwVwflZnlFJ9xlQTLRYHU4elabz6NPPTZxOpGEAQiO+6aCW0L2ZjS0FzIXee1sqvLFFQtP3UylUZHztg8dsVaeHcqVhLdQ+CQEDVE9aSKOBiv48Ab+ZDQu3shQExYvfDiBWqFQBBmjpv84QT3R4Thz1GOm1rTJ2O8WQuZHrRsBY4xK6IK1AMbHvUkEclD+5XDCaFXqdLe5MwtAd+xoUvSxqiXCIBMYKEjkApMBGp2GTHydwqfM4IUx/h+fhuAC69WGe5YJzcxnnGraCUD0FUtH7UOCnjnBEevw8QI+RyYWVJkLr1L89zBUzBSGMFVVwmmflu47qgGwkruVHMWrUCYV7n7VFvsWHR5MyqriUx5ePd5LJD5SsCumhui5ZrIhJHR8QIoqvuME2v5abkgpRQ3N/5n29p/Ac8aD1BQwBhqwAAAABJRU5ErkJggg==",
    32: "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAADPklEQVR42u2Xz28VVRTHP3deX1tKJfAoWlqQECUEUqOCGpGQEGOCNu6MyB9gMC7cuO2CxOjKjRtNdONWwg6Vqhs1shKJaDD+CMIzoYZasKC079fc83Ux782beTPvtY+QuOlJbs6dmXPnfs/3fO+9M7Bma/Y/m2t1drw29yjOzgDjPeJrwCcuCF8uv7Pz5t0AELQ6psa0vB+X9/RoQ/L+BWu4MxPH/xy5GwAGYiqsUZTcascdKBTC77a/emmu7xnFQiEovF5+b+e1FAALLY4ZHaxx4vBnTN5zq9er9jRbbOWbJd74+gjVsNgTQ2j2PfB2CgAWomb3pb3fcmzPub6TO7QNflso8eGFJ1YS3vpMCczCOGDDwBL4MHfw+XUP8OXoFL4tn5T9/cwmHnl8MXXPDK5+M8yNX4rNKuRoAAtpaUA+BN/IneDdDYdZDoa6p7cZRjdXMrd3ba1y/UQpYsApDeDFnzT41/n5fbXbDSSYn9zPx2yMkUptf+ufXanryCt1jcgdOzY1ggSF4eK+g9MaPHXU1R3AsR91XNL7UhTYvYmVY1YXi7lXzj5f+GAAIGzYhMn1PVmUqTDrD5AZIE3EJajXwVaVXTpm+0jk/7h9B0xZQgP1elSzfql+cL1DEpcWV44364gxJQEYwvVd04NbAsBx+rJfETytSWOfABCGYH1SOH2/4+nJaNk+O+k4fcViaiWBtSZWRHeHdxJ9akCUhuDAfQHP7Qg4NNE+N956ssCRbY5PLxtnr3puLKmp9A4fg8iUIKmBfCCBxMPjAfvHHFOl7P7z0Jhj/l9HZRm+WDTMJzIWTUaU8rkaQNlACbyJ2V+N2Z/F8ADMPFXk6N5oIz15MeTNr2os1xVnkso06VuTN5dBpIF680begFQWkV+qiJnPPbs3rQNgZraC913GWYva9DOXBGDV5jmQgzwrovazUz/UwaBR8W3RZerd7Z1KAjCkaE33YqHz2YVytKtZ1XKZansy726dFlEJahjyuULptZQulqMA3+iSsZQ+e1NfRoG1GaiFV7CkUPKyUGZDqVpnVn19Dv8eA9gyt/Gja6XF3TJ7DKOQzIKmN1mKyjs3ecmdW9h678m1n5I1A/gPKLi/hRJQtqQAAAAASUVORK5CYII=",
    48: "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",
}

# The GitHub mark (from GitHub's own octicons, MIT), pre-rendered as tiny PNGs so the exe needs no image library.
_GITHUB_MARK = {
    "light16": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAByklEQVR42o2SP2tUQRTFf3eGVVwMu82KxjDzlLVaEI2tTQhEsFVLEZVgLFLo97AKqCmMTbDTDyBIwH+VhRav9b23htcsEQISkkzyrs17Miwrya1mzpxz5s65I4yVc+6aiCwBc4AHUNUM+GCtfZll2Y+YL81ienq63Wq1VoD7MT5WqqqrxpgneZ7v/jOYmZk5Za19D1zneLUhIjfzPN81ANbalVq8JyJPga/APpABP4E9Vf1YnwVgTlWfAYj3fhb4VneTFUVxEZAkSU42bQ4GgxNpmgZAvfebwHmgOjw8vGJUdXHCm7URA6Rpug9oHUJVw8Za+8gA85Hw+VGPF5GVaDtvRCSJIv5+lMEY54IBTOR+5hgTOBc3ZIAiMliKDSeUFZHH0T633W73MjBbA77b7V7qdDob29vbu7Gy3+/3pqamXgML0YVvTVVVq3XCL+pAb4nIpnPuTkNMkuReCOEXcHv8VwqA9/4V8KAWb1VV5YbD4Xozul6vd7rdbv8GWpHBWlEUDw1ACGFZRD7VXZytf582zNFo9AfYisRfQgjLNIGVZblzcHBwQ1XfqeobEfn8vykCayGEhbIsdyYynHMD59ziBPyu9/7qOP4XYCmrzmlT0toAAAAASUVORK5CYII=",
    "light24": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAC9klEQVR42rWVT4gcVRDGf1VvhtklBmXBTXBn+rU7exDdiFHDBvWgEFBBL/65JCi5qtGTF0G8BrxJQi7mkEAQBEUPioogCIH8MYsh0VyE3e7eIcniIeSw2bVn+5WXXhlnerIzgn3qV9X1fa+/970q+J8fuVtyZmam6Zw7JCIHgHlgN2DADeAK8KOIfJYkyc2xCNrt9vTm5uZR4E2gts0mc+CkmX2YZdmtbQniOH7WzD4HpsdU4zrwWpqm54YSxHH8gpl9DTT+o+R3gJfTNP1pgKDVas2r6jngnjJ0q3yvbwPaBTaAneX6dlEU+zqdzh/06OtU9XQPOCLyVK1Wu57n+VsiclBELpeHSwhhl4g8KiJnGo3GyTzPZ0MIl8vSe51zp4GnARMA7/0h4Ezvtpxz9y0tLd0eRZc4jneb2Y3emJm9nmXZF1qujwxYI89HPmQR2VURfhdAm83mDLDQl7zS6XSWRyWYmpq6BvzeR/pMu92eVufc/n43icgJYHNUgsXFxS5woi+seZ7vV+DB/oKiKBbHbgkiAzXOuVk1sx39CVUN4xIURTFQY2Y7VUTuVHz/2LgEzrnHK8JramZJReJtQMfArwHvVMQTrdVqFyoST3jvP96u224pGkXRMTPbUyHbha2L9gvwZOmcq8BDwCTwTQjhg5WVld+GXLAFMzsKPFeh/8Usyxa0dMDxrV8C3lfVvcCfwEuqejWKou/n5uYaPcAT3vuzZna+Crx8jvU2O+e9v1Qe7lq3240bjcbDIYRTwE0ROZgkyb/Oynv/CvDlEPBf0zTdBxRbza4IIbyhqueBHfV6/aPl5eX3gNlhwm9sbPwwMTFBpXNUDwPFwDzw3r8IfFXOg+NmdsrMNM/za6urq2v9SN77os9tfwGvpmn67T8O6C1I0/Q7MztQTqcjInJJVS9OTk7eP4KbVkXk+V5wqryeZdlZM5sXkU+AdSCIyPoQ0PVy4Hxar9f3JEny81i3s9lsTnnv9w7LR1H0SKvVeuBuGH8Db1YKaG0G0+4AAAAASUVORK5CYII=",
    "light32": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAEI0lEQVR42sVXT2gcZRT/vW92k2yauGmTGAm7O5MwaTyIh8YiQhH/RSlBobVYPQjWP3gRUTy0wV7qzUNaUOtBxIp4ED1EFLSK1ktTaq304goN+++bya6lu6ldbeuys/M9L7Nh3cxkk90FH8zlvfd97/e9/wP8z0RbUR4bG9sWiUT2ANjFzBNENAQASqlVAFkiukhE53K5XKWrABKJxB4ArxDREwAiLdRvAFhUSr1j2/bFjgDEYrEpIcR7RPRomx7+UgjxWjablVsGYBjGc8x8EkB/h2H+i5lfsizrcz+hFmD8GDOfABDuQp71EtGBaDT6T7lcXmoJwDCMeWZ+q9vJTkSz0Wj0erlc/jkwBLquzwH4uom/CkAA2L5Fo38CUACGG3guMz9mWdaPdYZoyPTtAD5sBiWE2C+lHCai+wCc9tglAEsAfvC+swCueLJFpdRuKeUOZj7Y7HEi+nh6enqwzgg1+OgogDuan8HMywA4l8udB7BX1/UJKWXW78nxeHzctu1CA/g0M68rrkqlchjA0bUQxGKxHZqm2X4ZHwqFxtLp9NV2Aq/r+gSAjI/ob03T4plMpiw8pM8GlZvrupPtZh4zB50dVEo9s5YDRLQvQPFyKBS61C4AIcQSgOUA8X4AINM0ex3HKQPo9amd53O53KlO6s8wjEPM/JGP6NbIyMiQqFQqO/2MA2DHcb7qtAF4d7CPqL9UKplC07RYwNnVfD6/2ikA745rASGKC2beFnBWdbETsq8BpQaFEMIJODRqmuZtnVr2GtxwAABHKKVKQf27VqvNdeH1jwdNXSFEUfT09CxvUMdHGrvlVsk0zV4img+Sh8PhlEilUkUA6QCduw3DWGh3AjqOcxLAnQHyVCqVKtaH0TcbeOHVRCJxqnGAtKLx8fERXde/APDCBmrfrs2CRCIxQ0T1/a0K4E0iuqmUep2Ipjz+FQDvK6UWbdv+vblKvIa2y+twLwIYatGm77Es61dqGBxnADwIwAHwqRBivlqt1kKh0BKA6Yaz15VSs80LZzwe3y2EOANgYBNO+klK+dB/9gGl1GHvVWEAh5RSC/l8flUpdQBAfRpeJaK9ftuubdu/AHh7E8aVEOLIuoXEu+B4g+JTsVjMtG37N03Tdiql7u/r6zO9vQABk/OzTexm72az2Qu+K9nMzEy4VCp9D+ABj3XOcZzZQqFwa7MDUNd1p/FhTXR2YGDg4WQyWQ1cyycnJ6Ou634H4F6PlSSiBSJKuq57e61WO18oFEobLCFOQO+45LruIysrK9da/heMjo4O9Pf3fwJgn0/23mVZVnKLAE5rmvZ0JpMpr3OZ3yXFYvGGlPJJZn7Z227bpZsA3pBSzvkZxwaxAgC2LOsD13VNIjoG4A8AuUgkYrUwegFAGcAJAFNSyuNdnqzd/ev+F3qfqRGmUkGgAAAAAElFTkSuQmCC",
    "dark16": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABK0lEQVR42o2TsUoDQRCG/z1F9LCxULDTWkSMWFkIPoIgVsEqWAv6KBpEr7TyHQSjYmsniqYSxAcQkoj32czCuNwl+eG43X/+mZ3ZmZUSABvABfAG/Nj3CrSBNdUByIECKKlHaYGmU+cZ4I7xcfMvCHBphh5wBDwAfaALvBt/a7aBaU+jc8Ol3TUu+BOAKSDY+sO0v8DqpKSWpOBLCiEgqef2A2cu7Z9JOpTdcMSxRgA4cfrnTNKSsz9pNLxmObNUIhbGCLDoq5XdckQHyIakPwE8Ov2Lb2HEFTBX4TwPXCfacwGb1sYzYMd6/g3sOecD49OpbERBYeQusA00Y9/NPusGKKJI30EH+AL2ga2KEj6d8z2QV72Htk0YNQFKyzYfNigrQKuCbwLrKf8H3pYCeqCJfXsAAAAASUVORK5CYII=",
    "dark24": "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAB5ElEQVR42sWVwUtUURTGv/tUDIYIIx3JCBOGiAYzIzKUDFdJu3BVgWtz56Z/okUojRC16z9oURAIQiQVakE7IWZjlouIHIdpxpmfC++Dy3TfzHtv47e75/vOdw7vnnePdJwAzgGPgXfADkdoANvAG2AB6E9j3Ae8BGq0xz/gGdAT1/w28Ivk2AZutjO/A1RIj31gKso8D+w54t9ANYZpFfjrnP8AudDXWPMOSZ8kjTo1L0n6IWlO0n1JXyTtWC4raVjSK0kvJA1ZPsSapHFjDGH3DzydnUowFP2e/BlXsOYR5BIUuOLJXw3JATvbLr4CnQkKdAHfmjzqQF8gaSy8CwcFY8xB3ALGmJqkQlM4kDQWSLrgyVlP8eP7coYCSRkP0UhRwJdzMpBU9hAjKQqMemL7gaSih3gEBAkuuVPSvIcqCjgf8Yc+AUwM8wBYjvAYCEWfbaAGbABle34N5FuY3wBWIsw/usJZG9wCpoCLwK4jfgt0O/oTwPs2b9RDt0AHsGmJEnAGuAV8Bz4Ag57u77Uw37Dv23+vackKFmN8+0yEeQkYjkqadvbBEnANuA5kIvT1JvMKcLddZxN2O7kYjFHgJzAZd657gKd2mupANkJXsgvnOdCbZvmfBq624C8DZ1t5HAIYG4399zwA5QAAAABJRU5ErkJggg==",
    "dark32": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACdUlEQVR42sWXTUgVURTH/zNkLzR7+fT1RVEvbBHZJksMrI1Laxu0CHITtAoigsCgoJ0U5ToKokWLqKVUYIEZLSIIguwDXASJ6Hv2ZZimvxbdB5dh7sy8NxP+YRZzPv7n3Dv3nnNGWmF4tRgDTZJ6JO2TVJK03qjKkiYkvZL0wvO8+UyzBHqAe8Av4vEDuAPszyLwLuAR9eMhsL3e4CeBOdLjG3Cs1uCXyRbLwPmkwS/w/3AmLnifydbGDFCpI1jF+Nr4A/S6grcAkyFEhwEP6AaGjWwaeA48Mc+o5fugegOA3hC+z0BzWAJXHSvZFLArRezglsD7DgfnlaBjIeLEb0hxjUsOzu9AXpJ8Y3tCUqODZ2eKUuLybZZ03M70mSPTcSCXYgfWAO8d3I+rRjlg3mHUn0E17XdwzwENAvZGFI/WDBJoDbnaVez2JW11+JY9zyunbrf/OCoO9TZfUpNDuZxlQ3UdRl/SokNZBNZl8AlaJLk+5aIvaSZiWOnLYPVHIwafaQHFiHr+BliVYvU54F0Ef7Fq+CnC6EadwT3gZgTvR9t4KKaz3Q5tIO7gbcD9GM4h26HTUvwGzgGngQ+WfBK4CHQAvmO7DwKDwGyCdt0ZJBgxigXgFrDRFJHxgONs2MAJHDADaRKMyEGwZBndNfIOYMrIpoDuiK0fSBB8CehyEQxahgtAu5HngUNx5wBoT5DA9SiCBuCpZTwGNNZw+PzALgYxCqyOI8kDLy2nt6ajdQFHgLYY/0VH8NdAIelK1prZLgx76khguDoB1VpIToVMxLUk8BM4G3Zta0mkAFwCvgATCQ7iGPAVuAZsXpFfbiDxX/dfWnGxxt7xHY8AAAAASUVORK5CYII=",
}


def _enable_dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def _dark_title_bar(window: tk.Tk, dark: bool) -> None:
    """Match the Windows 11 title bar to the theme (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


class App:
    """The main window."""

    def __init__(self, root: tk.Tk, folder: Optional[Path] = None, auto_preview: bool = True):
        self.root = root
        self.dark = logic.system_prefers_dark()
        saved = logic.load_settings()  # last folder, grouping and "Subfolders" choice
        self.folder = tk.StringVar(value=str(folder or saved["folder"]))
        self.mode = tk.StringVar(value=saved["mode"])
        self.recursive = tk.BooleanVar(value=saved["recursive"])
        self.status = tk.StringVar(value="Pick a folder to tidy.")
        self.github_url = logic.GITHUB_URL
        self.moves: list = []
        self.skipped: set[int] = set()  # preview rows the user unticked
        self.view = "plan"  # "plan" (organize) or "dupes" (move extra copies aside)
        self.busy = False
        self.events: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._toast_job: Optional[str] = None
        self._toast_folder: Optional[Path] = None

        self._setup_window()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(50, self._drain_events)
        self.confirm = True  # ask before moving files (the release workflow's screenshot run turns this off)
        if auto_preview:
            self.root.after(150, self.preview)
        demo = os.environ.get("SFO_DEMO", "")  # release workflow screenshots: "organize" or "dupes"
        if demo == "organize":
            self.confirm = False
            self.root.after(1800, self.organize)
        elif demo == "dupes":
            self.root.after(1800, self.find_dupes)

    # ---------- look ----------
    def _setup_window(self) -> None:
        root = self.root
        root.title(logic.APP_TITLE)
        icon = logic.resource_path("icon.ico")
        if icon and sys.platform == "win32":
            try:
                root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        try:  # window + taskbar icon from the embedded PNGs (also works where .ico isn't supported)
            self._window_icons = [tk.PhotoImage(master=root, data=_APP_ICON[s]) for s in (48, 32, 16)]
            root.iconphoto(True, *self._window_icons)
        except tk.TclError:
            self._window_icons = []
        try:
            import sv_ttk  # Windows 11 "Sun Valley" look for ttk (tiny, pure Tcl)

            sv_ttk.set_theme("dark" if self.dark else "light", root)
        except Exception:
            ttk.Style(root).theme_use("vista" if sys.platform == "win32" else "clam")
        style = ttk.Style(root)
        family = self.family = "Segoe UI" if sys.platform == "win32" else "Selawik"
        self.fg_muted = "#9a9a9a" if self.dark else "#6b6b6b"
        self.title_font = (family + " Semibold", 15)
        self.byline_font = (family, 10)
        style.configure("Title.TLabel", font=self.title_font)
        style.configure("Byline.TLabel", font=self.byline_font, foreground=self.fg_muted)
        style.configure("Muted.TLabel", font=(family, 9), foreground=self.fg_muted)
        style.configure("Status.TLabel", font=(family, 10))
        style.configure("Footer.TLabel", font=(family, 8), foreground=self.fg_muted)
        style.configure("GitHub.TButton", font=(family, 9), padding=(8, 3))
        style.configure("Treeview", rowheight=26)
        self.scale = scale = root.winfo_fpixels("1i") / 96.0
        w, h = int(540 * scale), int(440 * scale)
        root.geometry(f"{w}x{h}")
        root.minsize(int(480 * scale), int(400 * scale))
        _dark_title_bar(root, self.dark)

    def _github_image(self) -> Optional[tk.PhotoImage]:
        want = 16 * self.scale
        px = min((16, 24, 32), key=lambda s: abs(s - want))
        try:
            return tk.PhotoImage(master=self.root, data=_GITHUB_MARK[f"{'dark' if self.dark else 'light'}{px}"])
        except tk.TclError:
            return None

    def _app_icon_image(self) -> Optional[tk.PhotoImage]:
        want = 24 * self.scale
        px = min((24, 32, 48), key=lambda s: abs(s - want))
        try:
            return tk.PhotoImage(master=self.root, data=_APP_ICON[px])
        except tk.TclError:
            return None

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=(PAD, PAD - 2, PAD, 6))
        outer.pack(fill="both", expand=True)

        # title row: "Smart File Organizer  by Abhinaba-Dev"  ...  [GitHub]
        head = ttk.Frame(outer)
        head.pack(fill="x")
        titles = ttk.Frame(head)
        titles.pack(side="left")
        self.logo_img = self._app_icon_image()
        if self.logo_img is not None:
            self.logo = ttk.Label(titles, image=self.logo_img)
            self.logo.pack(side="left", anchor="center", padx=(0, 8))
        ttk.Label(titles, text=logic.APP_TITLE, style="Title.TLabel").pack(side="left", anchor="s")
        # line the small text up on the title's baseline (both labels sit on the frame's bottom edge)
        lift = max(0, tkfont.Font(root=self.root, font=self.title_font).metrics("descent")
                   - tkfont.Font(root=self.root, font=self.byline_font).metrics("descent"))
        self.byline = ttk.Label(titles, text=logic.BYLINE, style="Byline.TLabel")
        self.byline.pack(side="left", anchor="s", padx=(8, 0), pady=(0, lift))
        self.github_img = self._github_image()
        self.github_btn = ttk.Button(head, text="GitHub", style="GitHub.TButton", cursor="hand2",
                                     command=self.open_github, takefocus=False)
        if self.github_img is not None:
            self.github_btn.configure(image=self.github_img, compound="left")
        self.github_btn.pack(side="right")

        ttk.Label(outer, text="Tidy a messy folder by type or date. Nothing moves until you say so.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 10))

        row = ttk.Frame(outer)
        row.pack(fill="x")
        self.entry = ttk.Entry(row, textvariable=self.folder)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.preview())
        self.browse_btn = ttk.Button(row, text="Browse\u2026", command=self.browse)
        self.browse_btn.pack(side="left", padx=(8, 0))

        modes = ttk.Frame(outer)
        modes.pack(fill="x", pady=(10, 8))
        ttk.Label(modes, text="Group", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.mode_buttons = []
        for key, label in logic.MODE_LABELS.items():
            b = ttk.Radiobutton(modes, text=label, value=key, variable=self.mode, command=self.preview)
            b.pack(side="left", padx=(0, 10))
            self.mode_buttons.append(b)
        self.sub_check = ttk.Checkbutton(modes, text="Subfolders", variable=self.recursive, command=self.refresh)
        self.sub_check.pack(side="right")

        # bottom rows first, so the list gives up space instead of pushing the buttons off a small window
        ttk.Label(outer, text=logic.FOOTER, style="Footer.TLabel").pack(side="bottom", anchor="e", pady=(6, 0))
        actions = ttk.Frame(outer)
        actions.pack(side="bottom", fill="x", pady=(2, 0))
        self.dupes_btn = ttk.Button(actions, text="Find duplicates", command=self.find_dupes)
        self.dupes_btn.pack(side="left")
        self.undo_btn = ttk.Button(actions, text="Undo last run", command=self.undo)
        self.undo_btn.pack(side="left", padx=(8, 0))
        self.organize_btn = ttk.Button(actions, text="Organize", style="Accent.TButton", command=self.organize)
        self.organize_btn.pack(side="right")
        self.preview_btn = ttk.Button(actions, text="Preview", command=self.preview)
        self.preview_btn.pack(side="right", padx=(0, 8))
        statusbox = ttk.Frame(outer)
        statusbox.pack(side="bottom", fill="x", pady=(8, 6))
        self.status_label = ttk.Label(statusbox, textvariable=self.status, style="Status.TLabel")
        self.status_label.pack(side="bottom", anchor="w")
        self.progress = ttk.Progressbar(statusbox, mode="determinate")

        table = ttk.Frame(outer)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("use", "file", "dest"), show="headings", selectmode="none",
                                 height=4)
        self.tree.heading("use", text="", anchor="center")
        self.tree.heading("file", text="File", anchor="w")
        self.tree.heading("dest", text="Goes to", anchor="w")
        self.tree.column("use", width=int(30 * self.scale), minwidth=int(30 * self.scale), stretch=False,
                         anchor="center")
        self.tree.column("file", width=220, anchor="w")
        self.tree.column("dest", width=180, anchor="w")
        self.tree.tag_configure("off", foreground=self.fg_muted)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double)
        bar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        bg = "#0f7b0f" if not self.dark else "#2e9e46"
        self.toast = tk.Frame(self.root, bg=bg, padx=14, pady=6)
        self.toast_text = tk.Label(self.toast, text="", bg=bg, fg="white", font=(self.family, 10))
        self.toast_text.pack(side="left")
        self.toast_link = tk.Label(self.toast, text="Open folder", bg=bg, fg="white", cursor="hand2",
                                   font=(self.family + " Semibold", 10, "underline"))
        self.toast_link.bind("<Button-1>", lambda _e: self.open_folder())
        self._refresh_buttons()

    # ---------- helpers ----------
    def current_folder(self) -> Optional[Path]:
        p = Path(self.folder.get().strip().strip('"')).expanduser()
        if not p.is_dir():
            self.show_error(NotADirectoryError(str(p)))
            return None
        return p.resolve()

    def included_moves(self) -> list:
        return logic.included(self.moves, self.skipped)

    def _refresh_buttons(self) -> None:
        folder = Path(self.folder.get().strip().strip('"')).expanduser()
        idle = "disabled" if self.busy else "normal"
        for b in (self.browse_btn, self.preview_btn, self.dupes_btn, self.sub_check, *self.mode_buttons):
            b.configure(state=idle)
        dupes = self.view == "dupes" and bool(self.moves)
        self.organize_btn.configure(text="Move extras to Duplicates" if dupes else "Organize",
                                    state="normal" if (self.included_moves() and not self.busy) else "disabled")
        self.undo_btn.configure(state="normal" if (not self.busy and folder.is_dir() and logic.can_undo(folder))
                                else "disabled")

    def fill(self, rows: list[tuple[str, str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, (a, b) in enumerate(rows):
            self.tree.insert("", "end", iid=str(i), values=(CHECK_ON, a, b))

    def _update_summary(self) -> None:
        chosen = self.included_moves()
        text = logic.duplicate_summary(chosen) if self.view == "dupes" else logic.plan_summary(chosen)
        if self.skipped:
            text += f" \u00b7 {len(self.skipped)} skipped"
        self.status.set(text)

    def toggle(self, index: int) -> None:
        """Tick or untick one preview row (unticked files stay where they are)."""
        if self.busy or not (0 <= index < len(self.moves)):
            return
        if index in self.skipped:
            self.skipped.discard(index)
            self.tree.item(str(index), tags=())
            self.tree.set(str(index), "use", CHECK_ON)
        else:
            self.skipped.add(index)
            self.tree.item(str(index), tags=("off",))
            self.tree.set(str(index), "use", CHECK_OFF)
        self._update_summary()
        self._refresh_buttons()

    def _on_tree_click(self, event) -> None:
        if self.tree.identify_column(event.x) == "#1":
            item = self.tree.identify_row(event.y)
            if item.isdigit():
                self.toggle(int(item))

    def _on_tree_double(self, event) -> None:
        if self.tree.identify_column(event.x) != "#1":
            item = self.tree.identify_row(event.y)
            if item.isdigit():
                self.toggle(int(item))

    def show_toast(self, text: str, folder: Optional[Path] = None) -> None:
        self.toast_text.configure(text=f"\u2713  {text}")
        self._toast_folder = folder
        if folder is not None:
            self.toast_link.pack(side="left", padx=(14, 0))
        else:
            self.toast_link.pack_forget()
        self.toast.place(relx=0.5, rely=1.0, y=-70, anchor="s")
        self.toast.lift()
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self._toast_job = self.root.after(6000 if folder is not None else 2600, self.toast.place_forget)

    def show_error(self, exc: BaseException) -> None:
        messagebox.showerror(logic.APP_TITLE, logic.friendly_error(exc), parent=self.root)

    def save_settings(self) -> None:
        folder = Path(self.folder.get().strip().strip('"')).expanduser()
        if folder.is_dir():
            logic.save_settings(str(folder.resolve()), self.mode.get(), self.recursive.get())

    def close(self) -> None:
        self.save_settings()
        self.root.destroy()

    def _run_bg(self, name: str, work: Callable[[], object]) -> None:
        """Run ``work`` off the UI thread; its result comes back through the event queue."""
        self.busy = True
        self._refresh_buttons()

        def target() -> None:
            try:
                self.events.put((name, work()))
            except BaseException as exc:  # shown as a friendly dialog
                self.events.put(("error", exc))

        threading.Thread(target=target, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                name, payload = self.events.get_nowait()
                getattr(self, f"_on_{name}")(payload)
        except queue.Empty:
            pass
        self.root.after(50, self._drain_events)

    # ---------- actions ----------
    def open_github(self) -> None:
        webbrowser.open(self.github_url)

    def open_folder(self) -> None:
        if self._toast_folder is not None:
            try:
                logic.open_in_explorer(self._toast_folder)
            except OSError as exc:
                self.show_error(exc)
        self.toast.place_forget()

    def browse(self) -> None:
        chosen = filedialog.askdirectory(parent=self.root, initialdir=self.folder.get(), title="Choose a folder to tidy")
        if chosen:
            self.folder.set(str(Path(chosen)))
            self.preview()

    def refresh(self) -> None:
        """Re-run whichever list is showing (after the Subfolders box changes)."""
        if self.view == "dupes":
            self.find_dupes()
        else:
            self.preview()

    def preview(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Looking through the folder\u2026")
        mode, recursive = self.mode.get(), self.recursive.get()
        self._run_bg("preview", lambda: (folder, logic.make_plan(folder, mode, recursive)))

    def _show(self, view: str, moves: list, rows: list[tuple[str, str]]) -> None:
        self.busy = False
        self.view = view
        self.moves = moves
        self.skipped = set()
        self.tree.heading("dest", text="Copy of" if view == "dupes" else "Goes to")
        self.fill(rows)
        self._update_summary()
        self._refresh_buttons()

    def _on_preview(self, payload) -> None:
        folder, moves = payload
        self._show("plan", moves, logic.preview_rows(moves, folder))
        self.save_settings()

    def organize(self) -> None:
        if self.busy:
            return
        moves = self.included_moves()
        if not moves:
            return
        folder = self.current_folder()
        if folder is None:
            return
        n = len(moves)
        files = f"{n} file{'s' if n != 1 else ''}"
        if self.view == "dupes":
            question = (f"Move {files} into the Duplicates folder?\n"
                        "Nothing is deleted, and Undo puts them back.")
        else:
            question = f"Move {files} into folders?\nYou can put everything back with Undo."
        if self.confirm and not messagebox.askyesno(logic.APP_TITLE, question, parent=self.root):
            return
        self.progress.configure(maximum=n, value=0)
        self.progress.pack(side="top", fill="x", pady=(0, 6))
        self.status.set("Moving files\u2026")
        self._run_bg("organized", lambda: (folder, logic.organize(
            moves, folder, on_progress=lambda m: self.events.put(("step", m)))))

    def _on_step(self, _move) -> None:
        self.progress.step(1)

    def _on_organized(self, payload) -> None:
        folder, result = payload
        self.busy = False
        self.progress.pack_forget()
        self.show_toast(logic.run_summary(result, "Moved" if self.view == "dupes" else "Organized"), folder)
        self.moves = []
        self.view = "plan"
        self.preview()

    def undo(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Putting files back\u2026")
        self._run_bg("undone", lambda: logic.undo_last(folder))

    def _on_undone(self, result) -> None:
        self.busy = False
        self.show_toast(logic.run_summary(result, "Put back"))
        self.view = "plan"
        self.preview()

    def find_dupes(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Checking file contents\u2026")
        recursive = self.recursive.get()
        self._run_bg("dupes", lambda: logic.duplicate_moves(folder, recursive))

    def _on_dupes(self, moves) -> None:
        self._show("dupes", moves, logic.duplicate_view(moves))

    def _on_error(self, exc: BaseException) -> None:
        self.busy = False
        self.progress.pack_forget()
        self.status.set("")
        self._refresh_buttons()
        self.show_error(exc)


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--self-test"]:  # used by the release workflow on the built .exe
        import tempfile

        out = Path(argv[1]) if len(argv) > 1 else None
        try:
            report = logic.self_test(Path(tempfile.mkdtemp(prefix="sfo-selftest-")))
            root = tk.Tk()
            root.withdraw()
            app = App(root, auto_preview=False)
            root.update()
            if app.github_url != logic.GITHUB_URL or app.byline.cget("text") != logic.BYLINE:
                raise RuntimeError("title row is missing the byline or the GitHub link")
            if app.logo_img is None or not app._window_icons:
                raise RuntimeError("app icon missing from the title row or the window")
            root.destroy()
            lines = report.lines + ["window ok"]
            code = 0 if report.ok else 1
        except BaseException as exc:
            lines, code = [f"FAILED: {exc!r}"], 1
        if out:
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return code
    _enable_dpi_awareness()
    root = tk.Tk()
    App(root, folder=logic.folder_from_argv(argv))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
