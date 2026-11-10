//! Projects and their files on disk.
//!
//! Layout under the data directory:
//!   projects/<id>.json          project metadata
//!   projects/<id>.history.json  agent conversation (raw Messages API turns)
//!   workspaces/<id>/            the project's files

use std::{
    path::{Component, Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};

use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};

/// Directories never shown in file listings or sent to the agent.
pub const IGNORED_DIRS: &[&str] = &[
    "node_modules",
    ".git",
    "target",
    ".next",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
];

/// Largest file the editor or agent will read, in bytes.
pub const MAX_READ_BYTES: u64 = 512 * 1024;

#[derive(Clone, Serialize, Deserialize)]
pub struct Project {
    pub id: String,
    pub name: String,
    /// Port reserved for this project's app; the preview points here.
    pub port: u16,
    pub created_at: u64,
}

#[derive(Serialize)]
pub struct FileEntry {
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

pub struct Workspaces {
    root: PathBuf,
}

pub fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

impl Workspaces {
    pub fn new(root: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(root.join("projects"))?;
        std::fs::create_dir_all(root.join("workspaces"))?;
        Ok(Self { root })
    }

    fn meta_path(&self, id: &str) -> PathBuf {
        self.root.join("projects").join(format!("{id}.json"))
    }

    pub fn history_path(&self, id: &str) -> PathBuf {
        self.root.join("projects").join(format!("{id}.history.json"))
    }

    pub fn dir(&self, id: &str) -> PathBuf {
        self.root.join("workspaces").join(id)
    }

    pub fn list(&self) -> Result<Vec<Project>> {
        let mut out = Vec::new();
        for entry in std::fs::read_dir(self.root.join("projects"))? {
            let path = entry?.path();
            let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if name.ends_with(".json") && !name.ends_with(".history.json") {
                let p: Project = serde_json::from_slice(&std::fs::read(&path)?)?;
                out.push(p);
            }
        }
        out.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        Ok(out)
    }

    pub fn get(&self, id: &str) -> Result<Option<Project>> {
        if !is_valid_id(id) {
            return Ok(None);
        }
        let path = self.meta_path(id);
        if !path.exists() {
            return Ok(None);
        }
        Ok(Some(serde_json::from_slice(&std::fs::read(path)?)?))
    }

    pub fn create(&self, name: &str) -> Result<Project> {
        let used: Vec<u16> = self.list()?.iter().map(|p| p.port).collect();
        let port = (4100..5000)
            .find(|p| !used.contains(p))
            .context("no free preview ports left")?;
        let project = Project {
            id: uuid::Uuid::new_v4().simple().to_string()[..12].to_string(),
            name: name.to_string(),
            port,
            created_at: now_secs(),
        };
        std::fs::create_dir_all(self.dir(&project.id))?;
        std::fs::write(self.meta_path(&project.id), serde_json::to_vec_pretty(&project)?)?;
        Ok(project)
    }

    pub fn delete(&self, id: &str) -> Result<()> {
        if !is_valid_id(id) {
            bail!("invalid project id");
        }
        let _ = std::fs::remove_dir_all(self.dir(id));
        let _ = std::fs::remove_file(self.history_path(id));
        std::fs::remove_file(self.meta_path(id))?;
        Ok(())
    }
}

fn is_valid_id(id: &str) -> bool {
    !id.is_empty() && id.len() <= 64 && id.chars().all(|c| c.is_ascii_alphanumeric())
}

/// Resolves a user- or agent-supplied relative path inside `base`.
/// Rejects absolute paths and any `..`, so nothing escapes the workspace.
pub fn resolve(base: &Path, rel: &str) -> Result<PathBuf> {
    let rel = rel.trim().trim_start_matches("./");
    let rel_path = Path::new(rel);
    let mut out = base.to_path_buf();
    for comp in rel_path.components() {
        match comp {
            Component::Normal(c) => out.push(c),
            Component::CurDir => {}
            _ => bail!("path must be relative to the project and must not contain '..': {rel}"),
        }
    }
    // Refuse to follow a symlink that points outside the workspace.
    if let (Ok(real), Ok(real_base)) = (out.canonicalize(), base.canonicalize()) {
        if !real.starts_with(&real_base) {
            bail!("path points outside the project: {rel}");
        }
    }
    Ok(out)
}

/// Lists files under `base/sub`, skipping heavy generated directories.
pub fn list_files(base: &Path, sub: &str, limit: usize) -> Result<Vec<FileEntry>> {
    let start = resolve(base, sub)?;
    let mut out = Vec::new();
    let mut stack = vec![start];
    while let Some(dir) = stack.pop() {
        let mut entries: Vec<_> = match std::fs::read_dir(&dir) {
            Ok(rd) => rd.filter_map(|e| e.ok()).collect(),
            Err(_) => continue,
        };
        entries.sort_by_key(|e| e.file_name());
        for entry in entries.into_iter().rev() {
            let name = entry.file_name().to_string_lossy().to_string();
            let Ok(meta) = entry.metadata() else { continue };
            let path = entry.path();
            let rel = path
                .strip_prefix(base)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            if meta.is_dir() {
                if IGNORED_DIRS.contains(&name.as_str()) {
                    continue;
                }
                stack.push(path);
            }
            out.push(FileEntry {
                path: rel,
                is_dir: meta.is_dir(),
                size: if meta.is_dir() { 0 } else { meta.len() },
            });
            if out.len() >= limit {
                break;
            }
        }
        if out.len() >= limit {
            break;
        }
    }
    out.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(out)
}

pub fn read_file(base: &Path, rel: &str) -> Result<String> {
    let path = resolve(base, rel)?;
    let meta = std::fs::metadata(&path).with_context(|| format!("file not found: {rel}"))?;
    if meta.is_dir() {
        bail!("{rel} is a directory");
    }
    if meta.len() > MAX_READ_BYTES {
        bail!("{rel} is too large to open ({} KB)", meta.len() / 1024);
    }
    let bytes = std::fs::read(&path)?;
    String::from_utf8(bytes).map_err(|_| anyhow::anyhow!("{rel} is not a text file"))
}

pub fn write_file(base: &Path, rel: &str, content: &str) -> Result<()> {
    let path = resolve(base, rel)?;
    if rel.trim().is_empty() {
        bail!("path is empty");
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(&path, content)?;
    Ok(())
}

pub fn delete_path(base: &Path, rel: &str) -> Result<()> {
    let path = resolve(base, rel)?;
    if path == base {
        bail!("refusing to delete the project root");
    }
    let meta = std::fs::symlink_metadata(&path).with_context(|| format!("not found: {rel}"))?;
    if meta.is_dir() {
        std::fs::remove_dir_all(path)?;
    } else {
        std::fs::remove_file(path)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_rejects_escapes() {
        let base = std::env::temp_dir();
        assert!(resolve(&base, "../etc/passwd").is_err());
        assert!(resolve(&base, "/etc/passwd").is_err());
        assert!(resolve(&base, "a/../../b").is_err());
        assert_eq!(resolve(&base, "./src/main.rs").unwrap(), base.join("src/main.rs"));
    }
}
