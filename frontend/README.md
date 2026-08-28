# 前端工程

`frontend/` 是 12345 Agent 的 React + TypeScript + Vite 前端工程，用于建设录音或文本输入、要素确认、工单审核、分类转派、处理结果录入和回复确认等界面。

## 快速开始

以下命令均在 `frontend/` 目录中执行：

```powershell
npm install
npm run dev
```

启动后访问 Vite 输出的本地地址，通常是：

- `http://localhost:5173`

## 常用脚本

```powershell
npm run dev      # 启动开发服务器
npm run build    # TypeScript 检查并生成生产构建
npm run lint     # 运行 ESLint
npm run preview  # 本地预览生产构建
```

## 环境变量

复制 `.env.example` 为 `.env.local` 后按需修改：

```powershell
Copy-Item .env.example .env.local
```

前端只能保存非敏感配置，例如后端 API 地址。所有模型 API Key、科大讯飞密钥和其他敏感信息只能保存在后端 `backend/.env`。

## 当前阶段

当前仍处于环境搭建阶段，`src/App.tsx` 保留 Vite 模板页面，用于验证 Node.js、npm、Vite、React 和 TypeScript 工具链是否正常。
