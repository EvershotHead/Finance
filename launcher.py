"""
A股量化分析系统 - 启动器
双击 exe 自动检测环境、安装依赖、启动应用
"""
import os
import sys
import subprocess
import importlib.util
import shutil
import tkinter as tk
from tkinter import messagebox
import threading
import webbrowser
import time


def find_python():
    """查找可用的 Python 路径
    
    优先级：
    1. 项目内置 .venv
    2. 系统 PATH 中的 python
    """
    project_dir = get_project_dir()
    
    # 优先检查项目内置 .venv
    venv_py = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_py):
        return venv_py
    
    # 查找系统 Python
    for name in ["python", "python3", "python.exe"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def get_project_dir():
    """获取项目目录（exe 所在目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def check_python(python_path=None):
    """检查 Python 版本"""
    if python_path is None:
        python_path = find_python()
    if not python_path:
        return False, "未找到 Python，请安装 Python 3.10+ 并添加到 PATH"
    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip()
        # 解析版本号
        parts = version_str.split()
        if len(parts) >= 2:
            ver = parts[1]
            major, minor = ver.split(".")[:2]
            if int(major) < 3 or (int(major) == 3 and int(minor) < 10):
                return False, f"Python {ver} 版本过低，需要 3.10+"
        return True, f"{version_str} ({python_path})"
    except Exception as e:
        return False, f"检测 Python 失败: {e}"


def check_and_install_deps(project_dir, python_path):
    """检查并安装缺失的依赖"""
    required = ['streamlit', 'pandas', 'numpy', 'plotly']
    missing = []
    for pkg in required:
        try:
            subprocess.run(
                [python_path, "-c", f"import {pkg}"],
                capture_output=True, timeout=15
            )
        except Exception:
            missing.append(pkg)
    
    if missing:
        return False, f"缺少依赖: {', '.join(missing)}"
    return True, "依赖检查通过"


def install_deps(project_dir, python_path):
    """安装依赖"""
    req_file = os.path.join(project_dir, "requirements.txt")
    if os.path.exists(req_file):
        try:
            subprocess.run(
                [python_path, "-m", "pip", "install", "-r", req_file, "-q"],
                cwd=project_dir,
                capture_output=True, text=True,
                timeout=300
            )
            return True, "安装完成"
        except Exception as e:
            return False, f"安装失败: {e}"
    return False, "找不到 requirements.txt"


def launch_app(project_dir, python_path):
    """启动 Streamlit 应用"""
    app_path = os.path.join(project_dir, "app.py")
    if not os.path.exists(app_path):
        return False, f"找不到 app.py: {app_path}"
    
    cmd = [
        python_path, "-m", "streamlit", "run", app_path,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]
    
    proc = subprocess.Popen(
        cmd,
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    return True, proc


class LauncherGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("A股量化分析系统")
        self.root.geometry("520x420")
        self.root.resizable(False, False)
        
        # 居中
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 520) // 2
        y = (self.root.winfo_screenheight() - 420) // 2
        self.root.geometry(f"+{x}+{y}")
        
        self.project_dir = get_project_dir()
        self.python_path = find_python()
        self.proc = None
        self._started = False
        
        self._create_widgets()
        self.root.after(100, self._initial_check)
        
        # 关闭窗口时清理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        """关闭窗口"""
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.root.destroy()
    
    def _create_widgets(self):
        """创建界面"""
        tk.Label(
            self.root,
            text="📈 A股量化分析系统",
            font=("微软雅黑", 20, "bold"),
            fg="#1f77b4"
        ).pack(pady=(20, 10))
        
        tk.Label(
            self.root,
            text="基于 AKShare / Tushare 的 A 股量化分析工具",
            font=("微软雅黑", 9), fg="#888"
        ).pack(pady=(0, 15))
        
        # 状态区域
        sf = tk.Frame(self.root)
        sf.pack(fill="x", padx=40, pady=5)
        
        self.python_lbl = tk.Label(sf, text="⏳ 检查 Python...", font=("微软雅黑", 10), anchor="w")
        self.python_lbl.pack(fill="x", pady=2)
        
        self.deps_lbl = tk.Label(sf, text="⏳ 检查依赖...", font=("微软雅黑", 10), anchor="w")
        self.deps_lbl.pack(fill="x", pady=2)
        
        self.app_lbl = tk.Label(sf, text="", font=("微软雅黑", 10), anchor="w")
        self.app_lbl.pack(fill="x", pady=2)
        
        # 日志
        self.log = tk.Text(
            self.root, height=7, width=58,
            font=("Consolas", 9), state="disabled",
            bg="#f5f5f5", fg="#333", relief="flat"
        )
        self.log.pack(padx=40, pady=10)
        
        # 按钮
        bf = tk.Frame(self.root)
        bf.pack(pady=10)
        
        self.start_btn = tk.Button(
            bf, text="🚀 启动分析系统",
            font=("微软雅黑", 13, "bold"),
            bg="#1f77b4", fg="white",
            width=16, height=1,
            relief="flat", cursor="hand2",
            command=self._on_start
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.browser_btn = tk.Button(
            bf, text="🌐 打开浏览器",
            font=("微软雅黑", 13),
            width=12, height=1,
            relief="flat", cursor="hand2",
            command=lambda: webbrowser.open("http://localhost:8501"),
            state="disabled"
        )
        self.browser_btn.pack(side="left", padx=10)
    
    def _log(self, msg):
        """写日志"""
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
    
    def _initial_check(self):
        """初始检查"""
        # Python
        ok, msg = check_python(self.python_path)
        if ok:
            self.python_lbl.config(text=f"✅ Python: {msg}", fg="green")
            self._log(f"[OK] Python: {msg}")
        else:
            self.python_lbl.config(text=f"❌ {msg}", fg="red")
            self._log(f"[ERROR] {msg}")
            messagebox.showerror("错误", msg + "\n\n请安装 Python 3.10+ 并确保添加到 PATH")
            return
        
        # 依赖
        ok, msg = check_and_install_deps(self.project_dir, self.python_path)
        if ok:
            self.deps_lbl.config(text=f"✅ {msg}", fg="green")
            self._log(f"[OK] {msg}")
        else:
            self.deps_lbl.config(text=f"⚠️ {msg}，正在安装...", fg="orange")
            self._log(f"[WARN] {msg}")
            self._log("[INFO] 正在安装依赖，请稍候...")
            threading.Thread(target=self._do_install, daemon=True).start()
    
    def _do_install(self):
        """后台安装依赖"""
        ok, msg = install_deps(self.project_dir, self.python_path)
        self.root.after(0, lambda: self._install_done(ok, msg))
    
    def _install_done(self, ok, msg):
        if ok:
            self.deps_lbl.config(text="✅ 依赖安装完成", fg="green")
            self._log("[OK] 依赖安装完成")
        else:
            self.deps_lbl.config(text=f"❌ {msg}", fg="red")
            self._log(f"[ERROR] {msg}")
            messagebox.showerror("安装失败", msg)
    
    def _on_start(self):
        """启动"""
        if self._started:
            return
        self._started = True
        self.start_btn.config(state="disabled", text="⏳ 启动中...", bg="#999")
        self.app_lbl.config(text="⏳ 正在启动 Streamlit...", fg="#666")
        self._log("[INFO] 正在启动应用...")
        threading.Thread(target=self._do_start, daemon=True).start()
    
    def _do_start(self):
        """后台启动应用"""
        ok, result = launch_app(self.project_dir, self.python_path)
        if not ok:
            self.root.after(0, lambda: self._start_fail(result))
            return
        
        self.proc = result
        
        # 等待启动
        time.sleep(4)
        
        # 检查进程是否还在
        if self.proc.poll() is not None:
            output = self.proc.stdout.read() if self.proc.stdout else ""
            self.root.after(0, lambda: self._start_fail(f"启动失败，退出码: {self.proc.returncode}\n{output[:200]}"))
            return
        
        self.root.after(0, self._start_ok)
    
    def _start_ok(self):
        """启动成功"""
        self.app_lbl.config(text="✅ 已启动: http://localhost:8501", fg="green")
        self._log("[OK] Streamlit 已启动")
        self._log("[INFO] 浏览器自动打开 http://localhost:8501")
        self.browser_btn.config(state="normal")
        self.start_btn.config(text="✅ 运行中", bg="#28a745")
        webbrowser.open("http://localhost:8501")
    
    def _start_fail(self, msg):
        """启动失败"""
        self.app_lbl.config(text=f"❌ {msg}", fg="red")
        self._log(f"[ERROR] {msg}")
        self._started = False
        self.start_btn.config(state="normal", text="🚀 启动分析系统", bg="#1f77b4")
        messagebox.showerror("启动失败", str(msg))
    
    def run(self):
        self.root.mainloop()


def main():
    """主入口"""
    if "--headless" in sys.argv:
        # 命令行模式
        project_dir = get_project_dir()
        python_path = find_python()
        
        print("=" * 50)
        print("  A股量化分析系统")
        print("=" * 50)
        
        if not python_path:
            print("❌ 未找到 Python，请安装 Python 3.10+")
            input("按 Enter 退出...")
            return
        
        ok, msg = check_python(python_path)
        print(f"Python: {msg}")
        if not ok:
            input("按 Enter 退出...")
            return
        
        ok, msg = check_and_install_deps(project_dir, python_path)
        if not ok:
            print(f"⚠️ {msg}，正在安装...")
            install_deps(project_dir, python_path)
        
        print("正在启动...")
        ok, proc = launch_app(project_dir, python_path)
        if ok:
            webbrowser.open("http://localhost:8501")
            print("✅ 已启动: http://localhost:8501")
            print("按 Ctrl+C 退出")
            try:
                proc.wait()
            except KeyboardInterrupt:
                proc.terminate()
        else:
            print(f"❌ {proc}")
            input("按 Enter 退出...")
        return
    
    # GUI 模式
    app = LauncherGUI()
    app.run()


if __name__ == "__main__":
    main()