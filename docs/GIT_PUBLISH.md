# Publish this project to Git over SSH

## 1. Check SSH access

For GitHub:

```bash
ssh -T git@github.com
```

For GitLab:

```bash
ssh -T git@gitlab.com
```

A successful authentication message is enough. It may still say shell access is disabled; that is normal.

## 2. Create an empty remote repository

Create an empty repo in GitHub/GitLab UI. Do not initialize it with README, `.gitignore`, or license if you want the cleanest first push.

Copy the SSH URL, for example:

```text
git@github.com:YOUR_USERNAME/speaking-trainer-app.git
```

## 3. Prepare and push

From the project root:

```bash
cd ~/Desktop/speaking-trainer-app
chmod +x scripts/git_publish_first_time.sh scripts/check_project.sh
./scripts/git_publish_first_time.sh git@github.com:YOUR_USERNAME/speaking-trainer-app.git
```

Replace the URL with your real SSH remote.

## 4. Future workflow

```bash
git status
git add .
git commit -m "Describe the change"
git push
```

## 5. Useful branch workflow

```bash
git checkout -b fix/some-issue
# make changes
git add .
git commit -m "Fix some issue"
git push -u origin fix/some-issue
```

Then open a pull request/merge request in your Git host.
