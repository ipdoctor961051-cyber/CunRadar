# CunRadar Admin

Cloudflare Worker + D1 管理后台。

## 部署

1. `npm install`
2. `npx wrangler d1 create cunradar-admin`
3. 将返回的数据库 ID 写入 `wrangler.jsonc`
4. `npx wrangler d1 execute cunradar-admin --remote --file migrations/0001_init.sql`
5. 设置三个 Worker Secrets：
   - `ADMIN_PASSWORD`：后台登录密码
   - `GITHUB_TOKEN`：仅允许操作本仓库 Actions 的 GitHub Token
   - `CONFIG_READ_TOKEN`：随机长字符串，供 GitHub Actions 读取关注列表
6. `npm run check && npm run deploy`
7. 在 GitHub Actions 中添加：
   - Secret `CUNRADAR_CONFIG_TOKEN`，值与 `CONFIG_READ_TOKEN` 相同
   - Variable `CUNRADAR_CONFIG_URL`，值为 `https://<worker-domain>/api/export`

后台使用 HTTP Basic Authentication。用户名可任意填写，密码必须等于 `ADMIN_PASSWORD`。
