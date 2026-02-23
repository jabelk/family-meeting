/**
 * AnyList Sidecar — Express REST API for AnyList grocery list operations.
 *
 * Provides endpoints for the family meeting assistant to push grocery lists
 * to AnyList, which syncs to Whole Foods for delivery ordering.
 *
 * Environment variables:
 *   ANYLIST_EMAIL    — AnyList account email
 *   ANYLIST_PASSWORD — AnyList account password
 *   PORT             — Server port (default 3000)
 */

const express = require("express");
const AnyList = require("anylist");

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const EMAIL = process.env.ANYLIST_EMAIL;
const PASSWORD = process.env.ANYLIST_PASSWORD;

if (!EMAIL || !PASSWORD) {
  console.error("ANYLIST_EMAIL and ANYLIST_PASSWORD are required");
  process.exit(1);
}

let anylist = null;
let authenticated = false;

async function ensureAuth() {
  if (authenticated && anylist) return;

  anylist = new AnyList({ email: EMAIL, password: PASSWORD });
  await anylist.login();
  await anylist.getLists();
  authenticated = true;
  console.log("AnyList authenticated successfully");
}

async function withReauth(fn) {
  try {
    await ensureAuth();
    return await fn();
  } catch (err) {
    if (err.message && (err.message.includes("401") || err.message.includes("auth"))) {
      console.log("Auth expired, re-authenticating...");
      authenticated = false;
      await ensureAuth();
      return await fn();
    }
    throw err;
  }
}

function findList(listName) {
  const name = (listName || "Grocery").toLowerCase();
  const list = anylist.getListByName(listName || "Grocery");
  if (list) return list;
  // Fallback: try partial match
  const lists = anylist.lists || [];
  return lists.find((l) => l.name.toLowerCase().includes(name));
}

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", authenticated });
});

// List all available lists
app.get("/lists", async (_req, res) => {
  try {
    const lists = await withReauth(async () => {
      await anylist.getLists();
      return (anylist.lists || []).map((l) => ({ name: l.name, id: l.identifier, itemCount: l.items.length }));
    });
    res.json({ lists });
  } catch (err) {
    console.error("GET /lists error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Get items from a list
app.get("/items", async (req, res) => {
  try {
    const items = await withReauth(async () => {
      await anylist.getLists();
      const list = findList(req.query.list);
      if (!list) return [];
      return list.items.map((item) => ({
        name: item.name,
        checked: item.checked || false,
        category: item.category || "",
      }));
    });
    res.json({ items });
  } catch (err) {
    console.error("GET /items error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Add a single item
app.post("/add", async (req, res) => {
  try {
    const { item, list: listName } = req.body;
    if (!item) return res.status(400).json({ error: "item is required" });

    await withReauth(async () => {
      await anylist.getLists();
      const list = findList(listName);
      if (!list) throw new Error(`List not found: ${listName || "Grocery"}`);
      const newItem = anylist.createItem({ name: item });
      await list.addItem(newItem);
    });
    res.json({ status: "added", item });
  } catch (err) {
    console.error("POST /add error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Add multiple items at once
app.post("/add-bulk", async (req, res) => {
  try {
    const { items, list: listName } = req.body;
    if (!items || !Array.isArray(items))
      return res.status(400).json({ error: "items array is required" });

    const added = await withReauth(async () => {
      await anylist.getLists();
      const list = findList(listName);
      if (!list) throw new Error(`List not found: ${listName || "Grocery"}`);

      let count = 0;
      for (const name of items) {
        const newItem = anylist.createItem({ name });
        await list.addItem(newItem);
        count++;
      }
      return count;
    });
    res.json({ status: "added", count: added });
  } catch (err) {
    console.error("POST /add-bulk error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Remove a single item by name
app.post("/remove", async (req, res) => {
  try {
    const { item, list: listName } = req.body;
    if (!item) return res.status(400).json({ error: "item is required" });

    await withReauth(async () => {
      await anylist.getLists();
      const list = findList(listName);
      if (!list) throw new Error(`List not found: ${listName || "Grocery"}`);
      const existing = list.items.find(
        (i) => i.name.toLowerCase() === item.toLowerCase()
      );
      if (existing) {
        await list.removeItem(existing);
      } else {
        throw new Error(`Item not found: ${item}`);
      }
    });
    res.json({ status: "removed", item });
  } catch (err) {
    console.error("POST /remove error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Clear all items from a list
app.post("/clear", async (req, res) => {
  try {
    const { list: listName } = req.body || {};
    const cleared = await withReauth(async () => {
      await anylist.getLists();
      const list = findList(listName);
      if (!list) throw new Error(`List not found: ${listName || "Grocery"}`);

      let count = 0;
      for (const item of [...list.items]) {
        await list.removeItem(item);
        count++;
      }
      return count;
    });
    res.json({ status: "cleared", count: cleared });
  } catch (err) {
    console.error("POST /clear error:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// Auth on startup, then start server
ensureAuth()
  .then(() => {
    app.listen(PORT, () => {
      console.log(`AnyList sidecar listening on port ${PORT}`);
    });
  })
  .catch((err) => {
    console.error("Failed to authenticate with AnyList:", err.message);
    // Start server anyway so health check reports unauthenticated
    app.listen(PORT, () => {
      console.log(`AnyList sidecar listening on port ${PORT} (unauthenticated)`);
    });
  });
