<#
.SYNOPSIS
    构建并推送 contract-risk 一体化镜像到阿里云 ACR（《09》第 8 节 / docs/ops/部署指南.md）。
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
$ImageTag = "${Registry}:${Tag}"

Write-Host "==> Build image: $ImageTag"
docker build -t $ImageTag .
if ($LASTEXITCODE -ne 0) { throw "镜像构建失败" }

Write-Host "==> Push image"
docker push $ImageTag
if ($LASTEXITCODE -ne 0) { throw "镜像推送失败" }

Write-Host "完成：$ImageTag"
