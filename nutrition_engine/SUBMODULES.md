# Wiring the three layer repos (submodules)

Use these steps **from the repo that contains `nutrition_engine`** (or from `nutrition_engine` if this directory is the git root). The workspace must already be a git repo (`git init` if needed).

## 1. Add the layer submodules

From the **git root** of this project (parent of `nutrition_engine` if the repo is one level up, or `nutrition_engine` if the repo root is inside it):

```bash
# Ensure you're in the git repo root, then:
cd nutrition_engine   # if your repo root is the parent of nutrition_engine

# Layer 1 (public)
git submodule add https://github.com/arjunpkulkarni/CulinAIAPP-Layer1.git layers/layer1

# Layer 2 (private — use SSH or a Personal Access Token)
git submodule add https://github.com/vedaankb/CulinAIAPP-Layer2.git layers/layer2
# If using HTTPS with a PAT: replace with
# git submodule add https://<YOUR_GITHUB_TOKEN>@github.com/vedaankb/CulinAIAPP-Layer2.git layers/layer2

# Or SSH (after adding your SSH key to GitHub):
# git submodule add git@github.com:vedaankb/CulinAIAPP-Layer2.git layers/layer2

# Layer 3 (private — same as Layer 2)
git submodule add https://github.com/vedaankb/CulinAIAPP-Layer3.git layers/layer3
# Or with PAT / SSH as above.
```

**Private repos (Layer 2 & 3):** You’re the owner, so you can:

- Use **SSH**: add your SSH key to GitHub, then use `git@github.com:vedaankb/...` URLs above, or  
- Use **HTTPS + Personal Access Token**: create a token (Settings → Developer settings → Personal access tokens), then use `https://<TOKEN>@github.com/vedaankb/...` when adding the submodule (the token is stored in `.gitmodules` and your local config; don’t commit it in plain text in code).

## 2. After adding submodules

- **First clone (for others):**  
  `git clone --recurse-submodules <this-repo-url>`  
  or after a normal clone:  
  `git submodule update --init --recursive`

- **Update submodules to latest:**  
  `git submodule update --remote --recursive`

## 3. Replace the in-repo stubs

Right now `layers/layer1`, `layers/layer2`, and `layers/layer3` are **stub packages** in this repo so the app runs without submodules. Once you add the real repos as submodules:

- Those directories will be **replaced** by the submodule content (git tracks the submodule commit, not our stub files).
- Each layer repo must expose the **engine contract** (see README and below), or we need **adapters** in this repo that wrap their API.

### Engine contract (no changes to layer repos required if they match)

| Layer | Startup | Request |
|-------|--------|--------|
| **Layer 1** | — | `estimate(item_name, description, modifiers)` → `{ "macros": {...}, "confidence": float }` |
| **Layer 2** | `load_calibration_tables(artifacts_path)` | `calibrate(baseline_estimate, restaurant_metadata)` → `{ "macros", "layer2_confidence", "applied_adjustments" }` |
| **Layer 3** | `load_embeddings(artifacts_path)` | `apply_layer3(l2_output)` → `{ "final_macros", "layer3_confidence", "refinements_applied" }` |

**Layer 1 (CulinAIAPP-Layer1):** The public repo is a FastAPI app with recipe/ingredient analysis and a DB (parser + calculator). It does **not** expose a single `estimate(item_name, description, modifiers)` at the top level. To integrate without changing that repo you can:

- Add a small **adapter** in this repo that builds an ingredient list from `item_name`/`description`, gets a DB session (Layer 1 DB must be set up and migrated), calls the parser + calculator, and maps the result to `{ "macros", "confidence" }`, or  
- Add a thin **entry point** in the Layer 1 repo that exposes that function; then this engine can call it directly.

Once Layer 2 and Layer 3 are cloned, confirm they expose `load_calibration_tables` / `load_embeddings` and `calibrate` / `apply_layer3` with the shapes above; if not, we can add adapters in this repo.
