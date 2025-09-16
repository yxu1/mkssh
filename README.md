# SSH配置管理工具

一个用于管理SSH连接配置并生成Tera Term和PuTTY连接脚本的Python工具。

## 功能特性

- 📝 从INI格式配置文件管理SSH连接配置
- 🖥️ 自动生成Tera Term连接批处理文件
- 🖱️ 自动生成PuTTY连接批处理文件
- 📋 自动生成系统SSH配置文件

## 文件结构

```
mkssh/
├── main.py              # 主程序文件
├── upper-case.ini       # 配置键名大小写映射文件
└── ssh-host.ini         # SSH主机配置文件（需手动创建，不被Git跟踪）
```

## 安装要求

- Windows 10+
- Python 3.11+
- Tera Term 或 PuTTY（可选，用于连接）

## 配置说明

### 1. 创建SSH主机配置文件

创建 `ssh-host.ini` 文件，格式如下：

```ini
[host-alias]
HostName = example.com
Port = 22
User = username
IdentityFile = C:\path\to\private\key
Password = your_password
ProxyType = http
ProxyHost = proxy.example.com
ProxyPort = 8080
ProxyUser = proxy_user
ProxyPassword = proxy_password
```

### 2. 配置键名映射

`upper-case.ini` 文件用于定义SSH配置键名的大小写映射：

```ini
[upper]
hostname = HostName
port = Port
user = User
identityfile = IdentityFile
password = Password
proxytype = ProxyType
proxyhost = ProxyHost
proxyport = ProxyPort
proxyuser = ProxyUser
proxypassword = ProxyPassword
```

## 使用方法

1. 编辑 `ssh-host.ini` 文件添加SSH主机配置
2. 运行主程序：
   ```bash
   python main.py
   ```
3. 程序会自动：
   - 生成Tera Term连接脚本到 `C:\1\tth\`
   - 生成PuTTY连接脚本到 `C:\1\pth\`
   - 更新系统SSH配置文件 (`~/.ssh/config`)

## 输出文件

- **Tera Term脚本**: `C:\1\tth\<host-alias>.bat`
- **PuTTY脚本**: `C:\1\pth\<host-alias>.bat`
- **SSH配置文件**: `~/.ssh/config`（自动备份原文件）

## 支持的配置选项

### 连接配置
- `HostName` - 主机地址
- `Port` - SSH端口（默认22）
- `User` - 用户名
- `IdentityFile` - 私钥文件路径
- `Password` - 密码

### 代理配置
- `ProxyType` - 代理类型（目前支持http）
- `ProxyHost` - 代理服务器地址
- `ProxyPort` - 代理服务器端口
- `ProxyUser` - 代理认证用户名
- `ProxyPassword` - 代理认证密码

## 开发说明

项目使用白名单模式的Git管理，默认只跟踪：
- `main.py`
- `upper-case.ini`

如需添加其他文件到版本控制，请编辑 `.gitignore` 文件。
