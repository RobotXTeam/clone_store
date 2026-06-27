#!/usr/bin/env python3
import os
import socket
import time
import sys
import re
import argparse
import subprocess
from pathlib import Path
from huggingface_hub import HfApi, login, hf_hub_url

# ==== 代理强制配置 ====
def get_proxy_port():
    import socket
    for port in [7897, 7890, 20171, 10809, 2080]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex(('127.0.0.1', port)) == 0:
                return port
    return 7890

PROXY_URL = f"http://127.0.0.1:{get_proxy_port()}"
os.environ["HTTP_PROXY"] = PROXY_URL
os.environ["HTTPS_PROXY"] = PROXY_URL
os.environ["ALL_PROXY"] = PROXY_URL

# ==== 存储路径配置 ====
BASE_DIR_HF = os.path.expanduser("~/.steven/downloads/huggingface")
BASE_DIR_GIT = os.path.expanduser("~/.steven/downloads/github")

def check_muniu_proxy():
    """
    深度检测代理配置，支持各种代理工具(Clash/Mihomo/V2ray/Sing-box)，
    验证当前使用的订阅是否包含 MUNIU。如果不包含，则强行中断。
    """
    import urllib.request
    import json
    import os
    import socket
    import time
    import re
    import subprocess
    
    muniu_keywords = ['muniu.pro', 'cnameip.xyz', 'muniu', '木牛', '专线；智能', '公网；智能', '公网节点', '专线节点']
    
    # 1. 优先尝试 Clash/Mihomo 的 REST API (端口常见为 9090, 9098等)
    for api_port in [9090, 9098, 9097]:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{api_port}/proxies")
            with urllib.request.urlopen(req, timeout=1) as response:
                data = json.loads(response.read().decode())
                proxies = data.get("proxies", {})
                # 检查 API 返回的节点中是否包含 MUNIU 特征
                for name, info in proxies.items():
                    info_str = str(info).lower()
                    if any(kw.lower() in name.lower() or kw.lower() in info_str for kw in muniu_keywords):
                        print(f"🛡️  流量保护检测通过: (API动态检测端口 {api_port}) 当前代理核心中包含 MUNIU 节点。")
                        return True
                # 如果 API 联通，但没有找到任何 MUNIU 节点，则说明在用其他付费订阅
                print(f"\n❌ 严重警告: 当前检测到代理服务 (端口 {api_port}) 正在运行，但未发现 MUNIU！")
                print("🛑 脚本已触发【防误耗流量机制】强行阻断下载。")
                sys.exit(1)
        except Exception:
            pass

    # 2. 检查 Clash Verge GUI 的动态配置文件
    paths = [
        "~/.local/share/io.github.clash-verge-ninja.clash-verge-ninja/profiles.yaml",
        "~/.config/io.github.clash-verge-rev.clash-verge-rev/profiles.yaml",
        "~/.config/clash-verge/profiles.yaml"
    ]
    for p in paths:
        full_path = os.path.expanduser(p)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    prof_content = f.read()
                match = re.search(r'^current:\s*([^\s]+)', prof_content, re.MULTILINE)
                if match:
                    current_uid = match.group(1).strip()
                    blocks = prof_content.split('- uid:')
                    for block in blocks:
                        if block.strip().startswith(current_uid):
                            if any(kw in block for kw in muniu_keywords):
                                print("🛡️  流量保护检测通过: (GUI配置检测) 当前生效代理为 MUNIU 订阅。")
                                return True
                            else:
                                name_match = re.search(r'^\s*name:\s*(.+)$', block, re.MULTILINE)
                                name = name_match.group(1).strip() if name_match else "未知订阅"
                                print(f"\n❌ 严重警告: 检测到你当前使用的代理订阅是 [{name}]，不是 MUNIU 订阅！")
                                sys.exit(1)
            except Exception:
                pass

    # 3. 兼容其他代理工具 (v2ray, sing-box, mihomo 服务端等)
    common_configs = [
        "/etc/mihomo/config.yaml",
        "/etc/clash/config.yaml",
        "/etc/v2ray/config.json",
        "/usr/local/etc/v2ray/config.json",
        "/etc/sing-box/config.json",
        os.path.expanduser("~/.config/mihomo/config.yaml"),
        os.path.expanduser("~/.config/clash/config.yaml"),
        os.path.expanduser("~/.config/v2ray/config.json"),
        os.path.expanduser("~/.config/sing-box/config.json")
    ]
    
    for conf in common_configs:
        if os.path.exists(conf):
            try:
                with open(conf, 'r', encoding='utf-8') as f:
                    conf_content = f.read()
                if any(kw in conf_content for kw in muniu_keywords):
                    print(f"🛡️  流量保护检测通过: (静态文件检测) 发现底层配置文件 {conf} 包含 MUNIU 节点。")
                    return True
            except Exception:
                pass

    # 4. 全局进程级别的特征扫描 (暴力破解检测)
    try:
        # 扫描含有常见代理名的进程命令行
        out = subprocess.check_output("ps aux | grep -E 'v2ray|sing-box|clash|mihomo|xray' | grep -v grep", shell=True).decode()
        if any(kw in out for kw in muniu_keywords):
            print("🛡️  流量保护检测通过: (进程级检测) 发现代理进程命令行中包含 MUNIU 特征。")
            return True
    except Exception:
        pass

    print("\n❌ 异常: 脚本扫描了所有代理工具(Clash/Mihomo/V2ray/Sing-box等)的运行状态及配置。")
    print("无法检测到任何包含 MUNIU 订阅 (muniu.pro) 的特征字眼。")
    print("🛑 脚本已自动触发【防误耗流量机制】强行阻断下载。请确保使用的是 MUNIU 节点！")
    sys.exit(1)

def parse_hf_url(url):
    url = url.replace('https://', '').replace('http://', '')
    if 'huggingface.co/' in url:
        path = url.split('huggingface.co/')[1]
        path = path.split('/tree/')[0]
        path = path.split('/blob/')[0]
        path = path.strip('/')
        return path
    return url.strip()

def run_hf_worker(repo_id, files_str, token):
    if token:
        login(token=token)
    
    repo_dir_name = repo_id.replace('/', '_')
    target_dir = os.path.join(BASE_DIR_HF, repo_dir_name)
    os.makedirs(target_dir, exist_ok=True)
    
    files = files_str.split(',')
    print(f"[{os.getpid()}] ===============================================")
    print(f"[{os.getpid()}] 开始后台下载 HuggingFace 模型，共 {len(files)} 个文件")
    print(f"[{os.getpid()}] 强制代理: {PROXY_URL}")
    print(f"[{os.getpid()}] 目标路径: {target_dir}")
    print(f"[{os.getpid()}] ===============================================\n")
    
    # 设定全局网络超时时间（60秒收不到任何数据包就果断抛出异常，拒绝假死）
    socket.setdefaulttimeout(60)

    for f in files:
        if not f: continue
        
        max_retries = 100
        retries = 0
        success = False
        
        while not success and retries < max_retries:
            try:
                import requests
                
                url = hf_hub_url(repo_id=repo_id, filename=f)
                dest_path = os.path.join(target_dir, f)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                tmp_path = dest_path + ".incomplete"
                
                if os.path.exists(dest_path):
                    if retries == 0:
                        print(f"[{os.getpid()}] ---> 文件已存在，跳过: {f}", flush=True)
                    success = True
                    break
                    
                downloaded = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
                
                if retries == 0 and downloaded == 0:
                    print(f"[{os.getpid()}] ---> 正在下载: {f}", flush=True)
                elif downloaded > 0:
                    print(f"[{os.getpid()}] ---> 继续下载: {f} (已下载 {downloaded/(1024*1024):.2f} MB)", flush=True)
                    
                headers = {}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                if downloaded > 0:
                    headers["Range"] = f"bytes={downloaded}-"
                    
                with requests.get(url, headers=headers, stream=True, timeout=(10, 60)) as r:
                    r.raise_for_status()
                    
                    if downloaded > 0 and r.status_code != 206:
                        downloaded = 0
                        os.remove(tmp_path)
                        
                    content_length = r.headers.get('Content-Length')
                    expected_total_size = downloaded + int(content_length) if content_length else None
                        
                    mode = "ab" if downloaded > 0 else "wb"
                    with open(tmp_path, mode) as f_out:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f_out.write(chunk)
                                
                final_size = os.path.getsize(tmp_path)
                if expected_total_size is not None and final_size != expected_total_size:
                    raise IOError(f"下载不完整: 期望 {expected_total_size} 字节，实际得到 {final_size} 字节。代理可能断开了连接。")
                    
                os.rename(tmp_path, dest_path)
                print(f"[{os.getpid()}] ---> 文件 {f} 下载完成！", flush=True)
                success = True
                
            except Exception as e:
                retries += 1
                downloaded = os.path.getsize(tmp_path) if os.path.exists(tmp_path) else 0
                print(f"[{os.getpid()}] 网络异常 ({type(e).__name__}: {e})，已下载 {downloaded/(1024*1024):.2f} MB，等待 3 秒重试... ({retries}/{max_retries})", flush=True)
                time.sleep(3)
            
    print(f"\n[{os.getpid()}] 🎉 所有请求的文件下载流程结束！")

def run_git_worker(url):
    repo_name = url.split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    if not repo_name:
        repo_name = "unknown_repo"
        
    target_dir = os.path.join(BASE_DIR_GIT, repo_name)
    os.makedirs(BASE_DIR_GIT, exist_ok=True)
    
    print(f"[{os.getpid()}] ===============================================")
    print(f"[{os.getpid()}] 开始后台克隆 GitHub 仓库: {url}")
    print(f"[{os.getpid()}] 强制代理: {PROXY_URL}")
    print(f"[{os.getpid()}] 目标路径: {target_dir}")
    print(f"[{os.getpid()}] ===============================================\n")

    if os.path.exists(target_dir) and os.listdir(target_dir):
        print(f"[{os.getpid()}] ❌ 目标文件夹 {target_dir} 已存在且不为空！中止克隆。")
        return

    cmd = ["git", "clone", url, target_dir]
    max_retries = 3
    
    env = os.environ.copy()
    # 针对 SSH 链接注入 ProxyCommand
    if url.startswith('git@') or url.startswith('ssh://'):
        # 使用 nc 走本地 HTTP 代理
        env['GIT_SSH_COMMAND'] = 'ssh -o "ProxyCommand nc -X connect -x 127.0.0.1:7890 %h %p"'
        
    for attempt in range(1, max_retries + 1):
        print(f"[{os.getpid()}] ---> 尝试克隆 (第 {attempt}/{max_retries} 次)...")
        try:
            subprocess.run(cmd, env=env, check=True)
            print(f"[{os.getpid()}] ✅ 克隆成功！路径: {target_dir}")
            break
        except subprocess.CalledProcessError as e:
            print(f"[{os.getpid()}] ❌ 克隆失败，退出码: {e.returncode}")
            if attempt < max_retries:
                import time
                time.sleep(3)
                print(f"[{os.getpid()}] 清理残留文件夹，准备重试...")
                subprocess.run(["rm", "-rf", target_dir])
            else:
                print(f"[{os.getpid()}] 🛑 已达到最大重试次数，克隆中止。")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true', help="内部使用参数：启动后台下载进程")
    parser.add_argument('--mode', type=str, choices=['hf', 'git'])
    parser.add_argument('--url', type=str)
    parser.add_argument('--repo_id', type=str)
    parser.add_argument('--files', type=str)
    parser.add_argument('--token', type=str, default="")
    args = parser.parse_args()

    if args.worker:
        if args.mode == 'hf':
            run_hf_worker(args.repo_id, args.files, args.token)
        elif args.mode == 'git':
            run_git_worker(args.url)
        sys.exit(0)

    # ==========================
    # 交互式前端界面
    # ==========================
    print("="*65)
    print("🚀 Clone Store - 全能断点下载器 (HuggingFace/GitHub 防断连)")
    print("="*65)
    
    check_muniu_proxy()
    
    print("\n请输入目标链接 (支持 Hugging Face 仓库 或 GitHub HTTPS/SSH 链接):")
    url = input("> ").strip()
    
    if 'github.com' in url:
        print("\n检测到 GitHub 链接！将执行 Git Clone 流程。")
        repo_name = url.split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
            
        target_dir = os.path.join(BASE_DIR_GIT, repo_name)
        os.makedirs(BASE_DIR_GIT, exist_ok=True)
        log_file = os.path.join(BASE_DIR_GIT, f"{repo_name}_clone.log")
        
        cmd = [
            sys.executable, os.path.abspath(__file__), 
            "--worker", "--mode", "git", "--url", url
        ]
        
        print(f"\n🔄 即将启动后台防断连脱机克隆进程。")
        print(f"📁 仓库将保存在: {target_dir}")
        print(f"🚀 网络连接: 强制代理 MUNIU (支持 HTTPS 和 SSH 自动代理)")
        
        with open(log_file, "a") as f_out:
            subprocess.Popen(
                cmd, 
                stdout=f_out, 
                stderr=subprocess.STDOUT, 
                start_new_session=True,
                stdin=subprocess.DEVNULL
            )
            
        print(f"\n✅ 成功将 Git Clone 任务提交到后台！")
        print(f"👉 即使立刻断开 SSH 或者网络波动，后台进程会自动重试。")
        print(f"🔍 如果你想查看实时日志，请运行命令:")
        print(f"   tail -f {log_file}")
        print(f"📦 或者查看已下载的文件夹大小:")
        print(f"   watch -n 2 du -sh {target_dir}")
        print("\n再见！👋")
        sys.exit(0)
        
    elif 'huggingface.co' in url:
        print("\n检测到 Hugging Face 链接！将执行模型下载流程。")
        print("🔑 如果你要下载受保护的模型 (如 Llama 3)，请输入 Access Token (公开模型直接回车跳过): ")
        token = input("> ").strip()
        
        if token:
            try:
                print("⏳ 正在验证 Token...")
                login(token=token)
                print("✅ 登录成功！")
            except Exception as e:
                print(f"❌ 登录失败: {e}")
                sys.exit(1)
                
        repo_id = parse_hf_url(url)
        if not repo_id:
            print("❌ 无法解析该 Hugging Face 链接。")
            sys.exit(1)
            
        print(f"\n⏳ 正在获取仓库 [{repo_id}] 的文件列表...")
        api = HfApi()
        try:
            files = api.list_repo_files(repo_id=repo_id)
        except Exception as e:
            print(f"❌ 获取文件列表失败: {e}")
            if "401 Client Error" in str(e) or "403 Client Error" in str(e) or "404 Client Error" in str(e):
                print("⚠️ 提示: 这是一个受保护的模型或仓库不存在，请重新运行脚本并输入有效的 Access Token。")
            sys.exit(1)
            
        files = [f for f in files if not f.startswith('.git')]
        
        print(f"\n📦 在 [{repo_id}] 中找到以下文件:")
        for i, f in enumerate(files, 1):
            print(f"{i}. {f}")
            
        all_idx = len(files) + 1
        print(f"{all_idx}. [ALL] (打包下载以上全部文件)")
            
        print(f"\n📝 请输入你想下载的文件编号（用空格或逗号分隔，或输入 '{all_idx}' 下载全部）:")
        choices = input("> ").strip()
        
        selected_files = []
        try:
            parts = choices.replace(',', ' ').split()
            if 'all' in [p.lower() for p in parts]:
                selected_files = files
            else:
                indices = [int(p) for p in parts]
                if all_idx in indices:
                    selected_files = files
                else:
                    for idx in indices:
                        if 1 <= idx <= len(files):
                            selected_files.append(files[idx-1])
                        else:
                            print(f"⚠️ 警告: 编号 {idx} 超出范围，已忽略。")
        except ValueError:
            print("❌ 输入格式错误，请输入数字编号。")
            sys.exit(1)
                
        if not selected_files:
            print("🛑 未选择任何文件，退出。")
            sys.exit(0)
            
        repo_dir_name = repo_id.replace('/', '_')
        target_dir = os.path.join(BASE_DIR_HF, repo_dir_name)
        os.makedirs(target_dir, exist_ok=True)
        log_file = os.path.join(target_dir, "download.log")
        
        files_arg = ",".join(selected_files)
        
        cmd = [
            sys.executable, os.path.abspath(__file__), 
            "--worker", "--mode", "hf",
            "--repo_id", repo_id, 
            "--files", files_arg
        ]
        if token:
            cmd.extend(["--token", token])
            
        print(f"\n🔄 即将启动后台脱机下载进程，共 {len(selected_files)} 个文件。")
        print(f"📁 下载目录统一归档于: {target_dir}")
        print(f"🚀 网络连接: 强制代理 MUNIU (已通过防刷流量检测)")
        
        with open(log_file, "a") as f_out:
            subprocess.Popen(
                cmd, 
                stdout=f_out, 
                stderr=subprocess.STDOUT, 
                start_new_session=True,
                stdin=subprocess.DEVNULL
            )
            
        print(f"\n✅ 成功将 Hugging Face 下载任务提交到后台！")
        print(f"👉 即使你立刻断开 SSH，下载也会稳健执行。")
        print(f"🔍 如果你想查看报错/运行日志，请运行命令:")
        print(f"   tail -f {log_file}")
        print(f"📦 由于后台无终端，进度条会被隐藏。请使用以下命令实时查看已下载文件的总大小:")
        print(f"   watch -n 2 du -sh {target_dir}")
        print("\n再见！👋")
        sys.exit(0)
        
    else:
        print("❌ 未识别的链接格式！请输入包含 github.com 或 huggingface.co 的链接。")
        sys.exit(1)

if __name__ == "__main__":
    main()
