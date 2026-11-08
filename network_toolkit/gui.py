"""Optional Tkinter desktop UI for VLSM allocation."""

import tkinter as tk
from tkinter import messagebox, ttk

from .vlsm import NetworkRequest, VLSMError, allocation_report


class VLSMApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Professional Network Toolkit – VLSM")
        self.geometry("1120x620")
        self.minsize(850, 480)
        self._build()

    def _build(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="VLSM Subnet Planner", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(root, text="Enter a parent IPv4 network and one subnet request per line.").pack(anchor="w", pady=(2, 12))

        controls = ttk.Frame(root)
        controls.pack(fill="x")
        ttk.Label(controls, text="Parent network:").pack(side="left")
        self.parent = tk.StringVar(value="192.168.10.0/24")
        ttk.Entry(controls, textvariable=self.parent, width=26).pack(side="left", padx=(8, 18))
        ttk.Label(controls, text="Subnets (name, hosts):").pack(side="left")

        self.requests = tk.Text(root, height=6, font=("Consolas", 10))
        self.requests.pack(fill="x", pady=8)
        self.requests.insert("1.0", "Users, 100\nServers, 50\nVoice, 20\nManagement, 10")
        ttk.Button(root, text="Calculate VLSM", command=self.calculate).pack(anchor="e", pady=(0, 10))

        columns = ("name", "requested", "network", "mask", "first", "last", "broadcast", "free")
        self.table = ttk.Treeview(root, columns=columns, show="headings", height=12)
        labels = ("Name", "Hosts", "Network / Prefix", "Netmask", "First usable", "Last usable", "Broadcast", "Free hosts")
        widths = (130, 70, 150, 145, 125, 125, 125, 85)
        for col, label, width in zip(columns, labels, widths):
            self.table.heading(col, text=label)
            self.table.column(col, width=width, anchor="w")
        self.table.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status).pack(anchor="w", pady=(8, 0))

    def calculate(self):
        try:
            requests = []
            for line_number, line in enumerate(self.requests.get("1.0", "end").splitlines(), 1):
                if not line.strip():
                    continue
                parts = line.rsplit(",", 1)
                if len(parts) != 2:
                    raise VLSMError(f"Line {line_number}: use format Name, Hosts")
                requests.append(NetworkRequest(parts[0].strip(), int(parts[1].strip())))
            report = allocation_report(self.parent.get().strip(), requests)
        except (ValueError, VLSMError) as exc:
            messagebox.showerror("VLSM calculation failed", str(exc))
            return

        for item in self.table.get_children():
            self.table.delete(item)
        for item in report["allocations"]:
            self.table.insert("", "end", values=(
                item["name"], item["requested_hosts"], item["network"], item["netmask"],
                item["first_usable"], item["last_usable"], item["broadcast_address"], item["unused_hosts"],
            ))
        self.status.set(
            f"{report['parent_network']} | {report['allocated_addresses']:,} allocated | "
            f"{report['remaining_addresses']:,} addresses remaining"
        )


def main():
    VLSMApp().mainloop()


if __name__ == "__main__":
    main()
