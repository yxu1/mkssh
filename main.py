#!/usr/bin/env python3
# coding = utf-8
"""
SSH配置管理工具
使用ssh-host.ini文件保存ssh主机连接信息
使用脚本转换成putty和teraterm的启动命令
"""

from typing import LiteralString


from configparser import ConfigParser
import os
import re
import configparser
import shutil
import datetime
from collections.abc import Mapping


CUDIR: str = os.path.abspath(os.path.dirname(__file__))  # 脚本文件所在目录
MY_CONF_FILE: str = os.path.join(CUDIR, 'ssh-host.ini')  # ssh-host配置文件
GITBASH_CONF_DIR: str = os.path.join('C:\\', '1', 'gitbash', 'ssh-host.d')  # 兼容其他脚本, 目前没有使用
SSH_CONF_FILE: str = os.path.join(os.environ.get('USERPROFILE') or '', '.ssh', 'config')  # 用户默认ssh配置目录, 目前没有使用
TTH_OUT_DIR: str = os.path.join('C:\\', '1', 'tth')  # tera term 命令行文件输出目录
PTH_OUT_DIR: str = os.path.join('C:\\', '1', 'pth')  # putty 命令行文件输出目录
USER_SSH_CFG_FILE: str = os.path.join(os.environ.get('USERPROFILE') or '', '.ssh', 'config')  # 输出ssh配置文件, 会生效
AUTO_SSH_CFG_FILE: str = os.path.join('C:\\', '1', 'ssh-cfg-auto-generate', 'config')  # 输出ssh配置文件, 不会生效, 除非 ssh -F 指定
UPPER_CONF_FILE: str = os.path.join(CUDIR, 'upper-case.ini')  # ini键名大写修正配置
SSHKEY_KEEP_DIR: str = os.path.join(CUDIR, 'sshkey')  # ssh密钥文件保存路径, ssh-host.ini中没有指定绝对路径, 则使用这个目录
SSHKEY_OUT_DIR: str = os.path.join('C:\\', '0', 'sshkey')  # ssh密钥文件输出目录, 因为原文件可能权限不对, 统一复制到这个目录, 处理权限


def has_path_component(name: str) -> bool:
    """
    判断是否包含路径信息（相对或绝对）。
    - 绝对路径: os.path.isabs(name) 为 True
    - 相对路径但含目录分隔符: 包含 os.sep 或（在 Windows）包含备用分隔符 '/' 或 '\\'
    """
    if not name:
        return False
    if os.path.isabs(name):
        return True
    # 兼容 Windows：可能混用 / 与 \
    seps = {os.sep}
    if os.altsep:
        seps.add(os.altsep)
    return any(s in name for s in seps)


def is_absolute_path(name: str) -> bool:
    """是否为绝对路径。"""
    return bool(name) and os.path.isabs(name)


class GenCmd:
    """SSH连接命令生成器类

    用于根据配置信息生成Tera Term和PuTTY的连接命令
    """
    def __init__(self, section: str, conf: Mapping[str, str]):
        self.section: str = section

        # 主连接配置
        self._connection_config: dict[str, str | None] = {
            'host': conf.get('HostName') or conf.get('Host') or section,
            'port': conf.get('Port'),
            'user': conf.get('User'),
            'password': conf.get('Password'),
            'keyfile': self.trans_keyfile_path(input_path=conf.get('IdentityFile')),
            'auth_type': conf.get('AuthType')
        }

        # 代理配置
        self._proxy_config: dict[str, str | None] = {
            'type': conf.get('ProxyType'),
            'host': conf.get('ProxyHost'),
            'port': conf.get('ProxyPort'),
            'user': conf.get('ProxyUser'),
            'password': conf.get('ProxyPassword')
        }

        # 自动推断认证类型
        if not self._connection_config['auth_type']:
            if self._connection_config['keyfile']:
                self._connection_config['auth_type'] = 'publickey'
            elif self._connection_config['password']:
                self._connection_config['auth_type'] = 'password'

    # 属性访问器
    @property
    def host(self) -> str | None:
        """获取SSH连接的主机地址
        
        Returns:
            主机地址字符串，如果未配置则返回None
        """
        return self._connection_config['host']

    @property
    def port(self) -> str | None:
        """获取SSH连接的端口号
        
        Returns:
            端口号字符串，如果未配置则返回None
        """
        return self._connection_config['port']

    @property
    def user(self) -> str | None:
        """获取SSH连接的用户名
        
        Returns:
            用户名字符串，如果未配置则返回None
        """
        return self._connection_config['user']

    @property
    def password(self) -> str | None:
        """获取SSH连接的密码
        
        Returns:
            密码字符串，如果未配置则返回None
        """
        return self._connection_config['password']

    @property
    def keyfile(self) -> str | None:
        """获取SSH连接的密钥文件路径
        
        Returns:
            密钥文件路径字符串，如果未配置则返回None
        """
        return self._connection_config['keyfile']

    @property
    def auth_type(self) -> str | None:
        """获取SSH连接的认证类型
        
        Returns:
            认证类型字符串，如果未配置则返回None
        """
        return self._connection_config['auth_type']

    @property
    def proxy_type(self) -> str | None:
        """获取代理类型
        
        Returns:
            代理类型字符串，如果未配置则返回None
        """
        return self._proxy_config['type']

    @property
    def proxy_host(self) -> str | None:
        """获取代理服务器主机地址
        
        Returns:
            代理主机地址字符串，如果未配置则返回None
        """
        return self._proxy_config['host']

    @property
    def proxy_port(self) -> str | None:
        """获取代理服务器端口号
        
        Returns:
            代理端口号字符串，如果未配置则返回None
        """
        return self._proxy_config['port']

    @property
    def proxy_user(self) -> str | None:
        """获取代理认证用户名
        
        Returns:
            代理用户名字符串，如果未配置则返回None
        """
        return self._proxy_config['user']

    @property
    def proxy_password(self) -> str | None:
        """获取代理认证密码
        
        Returns:
            代理密码字符串，如果未配置则返回None
        """
        return self._proxy_config['password']

    def trans_keyfile_path(self, input_path: str) -> str:
        keyfile_path: str = input_path
        if keyfile_path.startswith('~'):
            keyfile_path: str = os.path.expanduser(keyfile_path)
        if not is_absolute_path(name=keyfile_path):
            keyfile_path: str = os.path.join(SSHKEY_KEEP_DIR, keyfile_path)
        if os.path.dirname(keyfile_path) != SSHKEY_OUT_DIR:
            os.makedirs(name=SSHKEY_OUT_DIR, exist_ok=True)
            dst_path = os.path.join(SSHKEY_OUT_DIR, os.path.basename(keyfile_path))
            shutil.copy2(keyfile_path, dst_path)
            keyfile_path: str = dst_path
        return keyfile_path

    def tth(self, outfile: str) -> None:
        """生成Tera Term连接批处理文件
        
        Args:
            outfile: 输出批处理文件路径
        """
        # command for tera term ttssh
        # https://teratermproject.github.io/manual/5/en/commandline/ttssh.html
        exefile = '"%programfiles(x86)%\\teraterm5\\ttermpro.exe"'
        if self.proxy_type and self.proxy_type != 'none':
            if self.proxy_user:
                proxyarg = (f'-proxy {self.proxy_type}://{self.proxy_user}'
                           f':{self.proxy_password}@{self.proxy_host}:{self.proxy_port}')
            else:
                proxyarg = f'-proxy {self.proxy_type}://{self.proxy_host}:{self.proxy_port}'
        else:
            proxyarg = '-noproxy'
        if self.auth_type:
            autharg = f'/auth={self.auth_type}'
        else:
            autharg = '/ask4passwd'
        if self.user:
            autharg += f' /user={self.user}'
        if self.keyfile:
            autharg += f' /keyfile="{self.keyfile}"'
        if self.password:
            autharg += f' /password="{self.password}"'
        cmd = ''
        cmd += f'@echo off{os.linesep}'
        cmd += f'start "" {exefile} {proxyarg} {self.host}:{self.port}'
        cmd += f' /ssh {autharg} & {os.linesep}'
        with open(outfile, 'w', encoding='utf-8') as f:
            _ = f.write(cmd)
        # print(cmd)


    def trans_putty_keyfile_name(self, input_name:str) -> str:
        """转换SSH密钥文件名为PuTTY格式
        
        Args:
            input_name: 原始密钥文件名
            
        Returns:
            PuTTY格式的密钥文件名（.ppk扩展名）
        """
        if not input_name:
            raise ValueError("input_name cannot be empty")
        filename = os.path.basename(input_name)
        filedir = os.path.dirname(input_name)
        # 隐藏文件或仅扩展名（以单个点开头且仅一个点）：直接追加 .ppk
        if filename.startswith('.') and filename.count('.') == 1:
            new_filename = filename + '.ppk'
        else:
            base, sep, ext = filename.rpartition('.')
            # 若没有找到分隔点（sep为空），不移除扩展，直接在原名后加 .ppk
            new_filename = (base if sep else filename) + '.ppk'
        return os.path.join(filedir, new_filename)


    def pth(self, outfile: str) -> None:
        """生成PuTTY连接批处理文件
        
        Args:
            outfile: 输出批处理文件路径
        """
        # command for putty
        exefile = '"%programfiles%\\PuTTY\\putty.exe"'
        cork_exe = ('C:\\Program Files\\Tencent\\WeTERM\\resources\\'
                   'external\\win32\\x86\\corkscrew.exe')
        cmd = ''
        cmd += f'@echo off{os.linesep}'
        if self.proxy_type and self.proxy_type == 'http':
            # 暂时只支持http
            if self.proxy_user:
                cmd += f'set CORKSCREW_AUTH={self.proxy_user}:{self.proxy_password}{os.linesep}'
            proxyarg = ''' -proxycmd "\\"{}\\" {} {} %%host %%port"'''.format(
                cork_exe.replace("\\","\\\\"), self.proxy_host, self.proxy_port)
        else:
            proxyarg = ''
        autharg = ''
        if self.user:
            autharg += f' -l {self.user}'
        if self.keyfile:
            keyfile = self.trans_putty_keyfile_name(self.keyfile)
            autharg += f' -i "{keyfile}"'
        if self.password:
            autharg += f' -pw "{self.password}"'
        cmd += (f'start "" {exefile} -ssh -noshare {proxyarg} {autharg} '
                f'-P {self.port} {self.host} & {os.linesep}')
        with open(outfile, 'w', encoding='utf-8') as f:
            _ = f.write(cmd)


class HostConf:
    """SSH主机配置管理类"""
    def __init__(self):
        """初始化配置解析器并读取配置文件"""
        self.conf_parser: configparser.ConfigParser = configparser.ConfigParser()
        _ = self.conf_parser.read(MY_CONF_FILE, encoding='utf-8')
        # self.compat_file()
        # self.compat_dir()
        # 改成统一从ini生成ssh-config写入到系统目录, 所以不从系统的ssh配置目录解析ssh配置了. ssh-host.ini就是最全的配置.

    def compat_file(self) -> None:
        """从系统SSH配置文件兼容转换配置到ini格式"""
        hostlist: list[dict[str, str]] = []
        with open(SSH_CONF_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        hostnum = len(hostlist)
        idx = hostnum
        for line in lines:
            if (re.search(r'^\s*#', line) or re.search(r'^\s*$', line)):
                continue
            if re.search(r'^\s*\bHost\b', line):
                host = line.split('Host')[-1].split()[0]
                idx += 1
                hostlist.append({'Host': host})
            elif idx > hostnum:
                key = line.split()[0]
                value = ' '.join(line.split()[1:])
                if re.search(r'^/[A-Za-z]/', value):
                    value = value.replace('/', '', 1)
                    value = value.replace('/', ':\\', 1)
                    value = value.replace('/', '\\', -1)
                hostlist[idx-1][key] = value
        # print(hostlist)
        for i in hostlist:
            section: str | None = i.get('Host')
            if section is None or section.startswith('*'):
                continue
            if self.conf_parser.has_section(section):
                continue
            self.conf_parser.add_section(section)
            for key in i.keys():
                if key == 'Host':
                    continue
                if key == 'ProxyCommand':
                    # 暂时做不到从ProxyCommand提取出格式化的proxy配置, 忽略这个配置
                    continue
                self.conf_parser.set(section, key, i.get(key))


    def compat_dir(self) -> None:
        """从GitBash配置目录兼容转换配置到ini格式"""
        if not os.path.isdir(GITBASH_CONF_DIR):
            return None
        for i in os.listdir(GITBASH_CONF_DIR):
            full_path = os.path.join(GITBASH_CONF_DIR, i)
            if not (i.endswith('.cfg') and os.path.isfile(full_path)):
                continue
            lines: list[str] = []
            host: str | None = None
            with open(full_path, 'r', encoding='utf8') as f:
                for line in f.readlines():
                    if re.search(r'\bHost\b', line):
                        host = line.split('Host')[-1].split()[0]
                    if not (re.search(r'^\s*#', line) or re.search(r'^\s*$', line)):
                        # 仅在有 Host 后再记录有效行，避免无主机名配置
                        if host is not None:
                            lines.append(line)
            # 若未检测到 Host，跳过该文件
            if host is None:
                continue
            # print(f'{i}: {host}')
            if host.startswith('*'):
                continue
            if self.conf_parser.has_section(host):
                continue
            self.conf_parser.add_section(host)
            for line in lines:
                # print(line)
                key = line.split()[0]
                if key == 'Host':
                    continue
                value = ' '.join(line.split()[1:])
                self.conf_parser.set(host, key, value)



class FixUpper:
    """配置键名大小写转换类"""
    def __init__(self):
        """初始化并读取大小写转换配置文件"""
        self.conf_parser: ConfigParser = configparser.ConfigParser()
        _ = self.conf_parser.read(UPPER_CONF_FILE, encoding='utf-8')
        self.section: str = 'upper'
    def get(self, option: str) -> str:
        """获取配置键名对应的大写形式
        
        Args:
            option: 原始配置键名
            
        Returns:
            转换后的大写键名，如果未配置则返回原键名
        """
        s = self.section
        c = self.conf_parser
        o: str = option
        if c.has_option(s, o):
            return str(c.get(s, o, raw=True))
        else:
            return o



def main() -> None:
    """主函数：生成SSH配置和连接脚本"""
    conf_parser: ConfigParser = HostConf().conf_parser
    fix_upper = FixUpper()
    ssh_cfg_list: list[str] = []
    for section in conf_parser.sections():
        ssh_cfg_line = f'Host {section}'
        print(ssh_cfg_line)
        ssh_cfg_list.append(ssh_cfg_line + '\n')
        conf = conf_parser[section]
        for key in conf.keys():
            value = conf.get(key)
            key_with_upper = fix_upper.get(key)
            ssh_cfg_line = f'    {key_with_upper} {value}'
            print(ssh_cfg_line)
            ssh_cfg_list.append(ssh_cfg_line + '\n')
        cmd = GenCmd(section, conf)
        os.makedirs(TTH_OUT_DIR, exist_ok=True)
        cmd.tth(os.path.join(TTH_OUT_DIR, f'{section}.bat'))
        os.makedirs(PTH_OUT_DIR, exist_ok=True)
        cmd.pth(os.path.join(PTH_OUT_DIR, f'{section}.bat'))
    # AUTO_SSH_CFG_FILE 自动生成的文件, 不用备份
    with open(os.path.join(AUTO_SSH_CFG_FILE), 'w', encoding='utf-8') as f:
        f.writelines(ssh_cfg_list)
    # USER_SSH_CFG_FILE 写入之前加个备份
    try:
        user_cfg_path = os.path.join(USER_SSH_CFG_FILE)
        if os.path.isfile(user_cfg_path):
            ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            bak_path = f"{user_cfg_path}.bak-{ts}"
            _ = shutil.copy2(user_cfg_path, bak_path)
            _ = print(f"Backup created: {bak_path}")
    except (OSError, IOError) as e:
        _ = print(f"Warning: failed to backup {USER_SSH_CFG_FILE}: {e}")
    with open(os.path.join(USER_SSH_CFG_FILE), 'w', encoding='utf-8') as f:
        f.writelines(ssh_cfg_list)

if __name__ == '__main__':
    main()
