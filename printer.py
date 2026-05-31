# ==================== printer.py ====================
import os
import subprocess
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger('inkkeeper.printer')


def check_printer_status():
    """检查打印机连接状态"""
    connection = Config.PRINTER_CONNECTION

    if connection == 'cups':
        return _check_cups()
    elif connection == 'network':
        return _check_network()
    elif connection == 'script':
        return {'available': True, 'method': '自定义脚本', 'name': '脚本打印机'}
    else:
        return {'available': False, 'method': '未配置', 'name': '未检测到打印机'}


def _check_cups():
    """检查 CUPS 打印机状态"""
    try:
        result = subprocess.run(
            ['lpstat', '-p', Config.PRINTER_NAME],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            status = 'idle' if 'idle' in result.stdout.lower() else 'printing'
            return {
                'available': True,
                'method': 'CUPS',
                'name': Config.PRINTER_NAME,
                'status': status,
                'detail': result.stdout.strip()
            }
        else:
            # 尝试列出所有打印机
            list_result = subprocess.run(
                ['lpstat', '-p'], capture_output=True, text=True, timeout=10
            )
            printers = list_result.stdout.strip() if list_result.returncode == 0 else ''
            return {
                'available': False,
                'method': 'CUPS',
                'name': Config.PRINTER_NAME,
                'status': 'not_found',
                'detail': f'打印机 "{Config.PRINTER_NAME}" 未找到',
                'available_printers': printers,
            }
    except FileNotFoundError:
        return {
            'available': False,
            'method': 'CUPS',
            'name': 'N/A',
            'status': 'cups_not_installed',
            'detail': 'CUPS 未安装，请在容器中安装 cups-client'
        }
    except Exception as e:
        return {
            'available': False,
            'method': 'CUPS',
            'name': 'N/A',
            'status': 'error',
            'detail': str(e)
        }


def _check_network():
    """检查网络打印机"""
    ip = Config.PRINTER_IP
    if not ip:
        return {
            'available': False,
            'method': '网络直连',
            'name': 'N/A',
            'status': 'no_ip',
            'detail': '未配置打印机 IP 地址'
        }
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 9100))
        sock.close()
        if result == 0:
            return {
                'available': True,
                'method': '网络直连',
                'name': f'网络打印机 ({ip})',
                'status': 'online',
                'detail': f'已连接 {ip}:9100'
            }
        else:
            return {
                'available': False,
                'method': '网络直连',
                'name': f'网络打印机 ({ip})',
                'status': 'offline',
                'detail': f'无法连接 {ip}:9100'
            }
    except Exception as e:
        return {
            'available': False,
            'method': '网络直连',
            'name': 'N/A',
            'status': 'error',
            'detail': str(e)
        }


def print_image(filepath, job_name='InkKeeper保养打印'):
    """打印图片 — 根据配置选择打印方式"""
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"文件不存在: {filepath}")
        return False, f"文件不存在: {filepath.name}"

    connection = Config.PRINTER_CONNECTION

    try:
        if connection == 'cups':
            return _print_cups(filepath, job_name)
        elif connection == 'network':
            return _print_network(filepath, job_name)
        elif connection == 'script':
            return _print_script(filepath, job_name)
        else:
            return False, f"未知的打印方式: {connection}"
    except Exception as e:
        logger.error(f"打印异常: {e}")
        return False, str(e)


def _print_cups(filepath, job_name):
    """通过 CUPS 打印"""
    cmd = [
        'lp',
        '-d', Config.PRINTER_NAME,
        '-t', job_name,
        '-o', 'fit-to-page',
        str(filepath)
    ]
    logger.info(f"CUPS 打印命令: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0:
        logger.info(f"打印成功: {filepath.name} — {result.stdout.strip()}")
        return True, result.stdout.strip()
    else:
        logger.error(f"打印失败: {result.stderr}")
        return False, result.stderr.strip() or 'CUPS 打印失败'


def _print_network(filepath, job_name):
    """通过网络端口 9100 直接打印"""
    ip = Config.PRINTER_IP
    if not ip:
        return False, '未配置打印机 IP'

    try:
        import socket
        # 尝试通过 CUPS 转发到网络打印机
        cmd = [
            'lp',
            '-d', Config.PRINTER_NAME,
            '-h', 'localhost',
            '-t', job_name,
            '-o', 'fit-to-page',
            str(filepath)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or '网络打印失败'
    except Exception as e:
        return False, str(e)


def _print_script(filepath, job_name):
    """通过自定义脚本打印"""
    script = Config.PRINT_SCRIPT
    if not script:
        return False, '未配置打印脚本 (PRINT_SCRIPT)'

    script_path = Path(script)
    if not script_path.exists():
        return False, f'打印脚本不存在: {script}'

    cmd = [str(script_path), str(filepath), job_name]
    logger.info(f"脚本打印: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0:
        return True, result.stdout.strip() or '脚本打印完成'
    else:
        return False, result.stderr.strip() or '脚本打印失败'


def list_cups_printers():
    """列出所有 CUPS 打印机"""
    try:
        result = subprocess.run(
            ['lpstat', '-p', '-d'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return '未找到打印机'
    except FileNotFoundError:
        return 'CUPS 未安装'
    except Exception as e:
        return f'查询失败: {e}'
