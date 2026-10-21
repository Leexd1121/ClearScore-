# 发布到 GitHub

仓库建议名称：`clearscore`。建议简介：

> Offline sheet music cleanup for PDF, images and Word DOCX. Chinese, English, Russian and Uyghur desktop UI.

## 发布内容

- 提交源码、测试、README、MIT LICENSE、第三方声明和工作流。
- `docs/interface.png` 是合成测试图的界面截图，可以随源码发布。
- 不提交用户文档、处理结果、私人回归样本、`.git`、`.env`、`.venv`、`tmp`、`output`、`dist`。
- Windows 便携包作为 Release 附件上传，不作为 Git 源文件提交。

## 使用 GitHub 网页

1. 使用愿意公开关联的 GitHub 账号或组织。先在邮箱设置启用 **Keep my email addresses private**，再创建名为 `clearscore` 的公共空仓库。
2. 解压 `ClearScore-1.1.0-source.zip`，进入 `ClearScore` 文件夹，将其中的文件和目录上传到仓库根目录，包含 `.github`、`.gitignore` 和 `.gitattributes`。不要只上传 ZIP 文件本身，也不要上传原始开发工作目录。
3. 本地 Git 推送方式更适合后续维护，见下方命令。
4. 在 Actions 页面检查自动测试和 Windows 构建结果。
5. 创建 `v1.1.0` Release，附加本地或 Actions 生成的便携 ZIP。

源码包已包含 MIT LICENSE、完整四语界面、合成测试素材和构建工作流。便携包应上传到 Release 附件；网页仓库上传单文件限制为 25 MiB。参见 [GitHub 文件上传说明](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) 和 [大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

GitHub 会公开仓库所有者和相关操作账号；源码脱敏不能匿名化平台账号。邮箱设置说明见 [GitHub 官方文档](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address)。

## 使用 GitHub CLI（开发者）

在**源码包新解压出的** `ClearScore` 文件夹执行。下面只为该仓库设置通用提交署名，使用保留的 `.invalid` 域名，不填写真实姓名或个人邮箱：

```powershell
git init -b main
git config --local user.name "ClearScore contributors"
git config --local user.email "contributors@clearscore.invalid"
python scripts/package_source.py --check
git add .
git commit -m "Initial release of ClearScore"
gh auth login
gh repo create clearscore --public --source=. --remote=origin --push
```

通用署名不关联 GitHub 贡献统计。如希望关联贡献，可以改用 GitHub 提供的 `noreply` 邮箱，但账号标识会公开。登录只在 GitHub CLI 的交互流程里完成，不把 token 写进源码、远程 URL 或命令示例。

上传源码后，在网页创建 `v1.1.0` Release，选择经过检查的 Windows ZIP 作为附件。也可等 Actions 构建成功后下载生成的便携包。以上为操作说明，不表示已经创建远程仓库。

## 后续版本

发布前运行 `python scripts/package_source.py`，得到通过清单及隐私检查的源码 ZIP 和 `SOURCE-AUDIT.json`。所有新增文件需要加入公开清单，私人样本保持在清单外。检查方式和范围见[隐私说明](PRIVACY.md)。
