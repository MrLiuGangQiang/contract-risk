<#
.SYNOPSIS
    构建并推送 contract-risk 前后端镜像到阿里云 ACR（《09》第 8 节 / docs/ops/部署指南.md）。
.DESCRIPTION
    用法：.\scripts\build-and-push.ps1 -Tag v0.1.0
    前置：已登录 ACR（docker login registry.cn-hangzhou.aliyuncs.com）。
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Tag
)

$ErrorActionPreference = "Stop"
$Registry = "registry.cn-hangzhou.aliyuncs.com/liugangqiang/contract-risk"
$BackendTag = "${Registry}:backend-${Tag}"
$FrontendTag = "${Registry}:frontend-${Tag}"

Write-Host "==> Build backend image: $BackendTag"
docker build -f backend/Dockerfile -t $BackendTag backend
if ($LASTEXITCODE -ne 0) { throw "后端镜像构建失败" }

Write-Host "==> Build frontend image: $FrontendTag"
docker build -f frontend/Dockerfile -t $FrontendTag frontend
if ($LASTEXITCODE -ne 0) { throw "前端镜像构建失败" }

Write-Host "==> Push backend image"
docker push $BackendTag
if ($LASTEXITCODE -ne 0) { throw "后端镜像推送失败" }

Write-Host "==> Push frontend image"
docker push $FrontendTag
if ($LASTEXITCODE -ne 0) { throw "前端镜像推送失败" }

Write-Host "完成：$BackendTag / $FrontendTag"
