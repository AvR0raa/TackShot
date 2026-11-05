# TackShot 云代理部署（L2 方案）

目标：百度 APPID/密钥、SimpleTex Token **只存云端**，安装包里只有一个代理 URL。
泄露防护：URL 泄露无害，随时可换；如配置了 PROXY_KEY，可一键作废旧客户端。

两个等价实现，任选其一：

| 实现 | 文件 | 适合 | 免费额度 |
| --- | --- | --- | --- |
| Cloudflare Workers | `cloud/worker.js` | 部署最简单（网页粘贴即可） | 10 万请求/天；国内直连 workers.dev 不稳，建议绑自定义域名 |
| 腾讯云函数 SCF | `cloud/scf_main.py` | 国内访问快 | 按量计费，个人用量月成本 ≈ 0 |

## A. Cloudflare Workers 部署

1. 注册 [cloudflare.com](https://dash.cloudflare.com/sign-up)，进入 **Workers & Pages** → Create Worker
2. 编辑代码：整个 `cloud/worker.js` 粘贴进去 → Deploy
3. 设置密钥（Settings → Variables and Secrets → Add，类型选 **Secret**）：
   - `BAIDU_APPID` = 你的 APPID
   - `BAIDU_SECRET` = 你的密钥
   - `SIMPLETEX_TOKEN` = 你的 UAT（不需要公式识别可不设）
   - `PROXY_KEY`（可选，止损开关；设置后客户端请求必须带对应 key）
4. 验证：浏览器访问 `https://<worker名>.<账号名>.workers.dev/health` 应返回 `{"ok":true,...}`
5. 把该 URL 填入本地 `tools/proxy_local.json`（见下），重新构建

## B. 腾讯云函数 SCF 部署（详细步骤）

> 全程约 10 分钟。个人量级（月几千次调用）费用 ≈ 0～1 元（按量计费：GB-秒 + 调用次数）。

### B0. 前置

1. 注册腾讯云账号（<https://cloud.tencent.com>），完成**实名认证**（必须，否则无法创建函数）
2. 微信扫码登录即可；无需绑定信用卡

### B1. 创建函数

1. 控制台搜索「**云函数**」（Serverless Cloud Function，SCF）进入产品页，点「**立即使用**」（首次会提示开通服务，同意即可）
2. 「函数服务」→「**新建**」→ 选择「**自定义创建**」：
   - 创建方式：自定义创建
   - 函数名称：`tackshot-proxy`（任意）
   - 地域：**广州 / 上海 / 北京任一**（选离你近的；决定 URL 前缀）
   - 运行环境：**Python 3.9**（其他 3.x 也可以）
   - 内存：**256 MB**（128 也够，256 留余量）
   - **执行超时时间：60 秒**（默认 3 秒必超时！图片翻译要传 4MB 图片）
   - 日志投递：默认（CLB 免费额度内，方便排错）
3. 「函数代码」页签：编辑器里**删掉模板代码**，把 `cloud/scf_main.py` 的内容整个粘贴进去，点「**部署**」
4. 「函数管理 → 函数配置」确认：执行方法为 `scf_main.main_handler`
   （如果文件名保存为 index.py 就是 `index.main_handler`，与文件名对应即可）

### B2. 配置密钥（环境变量）

「函数配置」→「编辑」→「环境变量」，逐条添加（值填你自己的）：

| 键 | 值 | 说明 |
| --- | --- | --- |
| `BAIDU_APPID` | 你的百度 APPID | 必填 |
| `BAIDU_SECRET` | 你的百度密钥 | 必填 |
| `SIMPLETEX_TOKEN` | 你的 SimpleTex UAT | 不用公式识别可不填 |
| `PROXY_KEY` | 自定义随机串 | **可选**：设置后客户端必须带对应 key（作废旧版时用，先不设） |

保存。这些值只存在腾讯云端，加密存储，任何日志不会打印。

### B3. 开启函数 URL（触发器）

1. 「触发管理」→「**函数 URL**」→ 创建：
   - 鉴权方式：**免鉴权**（Public，任何人可访问；靠 PROXY_KEY 做软限制）
   - 集成响应：**开启**（代码返回的是 `{statusCode, body}` 结构，必须开）
   - 请求方法：勾选 **GET + POST**
2. 创建后得到形如 `https://xxxx-xxxx-xxxx.gz.apigw.tencentcs.com/release/` 的 URL
   （老版是 `<函数id>.<地域>.apigw.tencentcs.com/release/`；**结尾的 `/release` 保留**，别多删或多加斜杠）

> 包体限制：函数 URL 底层走 API 网关，请求体上限大于 4MB（百度图片翻译本身就限 4MB，
> 客户端超限会提前报错），正常使用不会碰到。如果遇到 HTTP 413，把情况反馈到 issue。

### B4. 验证

浏览器或 curl（Git Bash 自带）：

```bash
# 1) 探活：应返回 {"ok": true, "service": "tackshot-proxy"}
curl https://<你的函数URL>/health

# 2) 文本翻译链路：应返回百度 JSON（含 trans_result，dst 为中文）
curl -X POST https://<你的函数URL>/text \
     -d "q=Hello, world" -d "from=en" -d "to=zh"
```

第 2 步通了就说明：函数 URL → 云函数 → 签名 → 百度，整条链路正确。

### B5. 客户端接入

把 URL（不带结尾斜杠）写入 `tools/proxy_local.json`：

```json
{ "proxy_url": "https://xxxx.gz.apigw.tencentcs.com/release" }
```

重新 `build.ps1`（控制台会打印 `managed proxy: <URL>`）→ `build_setup.ps1`。

### B6. 运维 / 应对

| 场景 | 操作 |
| --- | --- |
| 查错 | 函数「日志查询」页签，看每次调用的返回与报错 |
| 改密钥 | 「函数配置 → 环境变量」改完保存即生效，客户端无需更新 |
| 作废旧客户端 | 加 `PROXY_KEY` 环境变量，同时更新客户端构建里的 key（联系开发者） |
| 换 URL | 重新创建函数 URL，旧 URL 自动失效，新版客户端内置新 URL |
| 防超支 | 「函数配置」可设并发上限；百度侧图片翻译 1000 次/月自动封顶 |

### 常见坑

- **默认超时 3 秒**：图片翻译必挂。务必改成 60s（B1 步骤已强调）
- **集成响应没开**：客户端收到的是网关包装的错误 JSON。B3 步骤必须勾选
- **入口函数名**：`文件名.函数名`。保存文件叫 `scf_main.py` 就是 `scf_main.main_handler`
- **地域**：函数 URL 的域名由地域决定，选国内地域延迟最低

## 客户端构建（注入代理 URL）

```powershell
# tools/proxy_local.json（不入库，被 .gitignore 排除）
{ "proxy_url": "https://xxx.example.workers.dev" }

powershell -ExecutionPolicy Bypass -File tools/build.ps1    # 自动生成 src/proxy_embedded.inc
powershell -ExecutionPolicy Bypass -File tools/build_setup.ps1
```

- 有 `proxy_local.json`：构建出「内置代理」版，用户装完即用（公共额度）
- 没有：构建出「无内置」版，行为与现在一致（用户自配凭据）
- GitHub 源码永远只含空模板，不含 URL 与任何密钥

## 运行时行为（src/managed.cpp）

凭据优先级：**用户自配（设置 → 识别）> 内置云代理**。
- 用户填了自己的百度凭据/SimpleTex Token → 直连官方 API（现状不变）
- 未填 → 走内置代理：客户端只发图片/文本 + 语言参数，**签名与密钥都在云端完成**
- 环境变量 `TACKSHOT_MANAGED_PROXY` 可覆盖内置 URL（测试 / 代理迁移用）

## 泄露应对

1. 换代理：部署新 Worker / 改函数 URL → 新版客户端内置新 URL
2. 作废旧版：设置 `PROXY_KEY` 并在客户端构建里更新 → 旧安装包失效
3. 百度密钥本身自始至终未离开云端，无需更换

## 限流 / 用量统计（可选升级）

Workers 可绑 KV / D1 做每客户端计数；SCF 可写 COS / 日志服务做月度统计。
当前 v1 依赖百度侧月度额度自然封顶（图片翻译 1000 次/月，文本标准版 QPS=1）。
