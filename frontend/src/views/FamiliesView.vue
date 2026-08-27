<script setup>
import { ref, onMounted } from "vue";
import { useFamiliesStore } from "@/stores/families";
import { toast } from "@/composables/useToasts";
import Sidebar from "@/components/Sidebar.vue";

const families = useFamiliesStore();
const mobileSidebar = ref(false);

const newName = ref("");
const newDesc = ref("");
const creating = ref(false);

const editingId = ref(null);
const editName = ref("");
const editDesc = ref("");
const saving = ref(false);

const uploadingFor = ref(null);
const fileInputs = ref({});

onMounted(async () => {
  await families.load(true).catch((e) => toast(e.message, "error"));
});

async function create() {
  const name = newName.value.trim();
  if (!name) return;
  creating.value = true;
  try {
    await families.create({ name, description: newDesc.value.trim() || null });
    newName.value = "";
    newDesc.value = "";
    toast("Family created", "success");
  } catch (e) {
    toast(e.message, "error");
  } finally {
    creating.value = false;
  }
}

function startEdit(f) {
  editingId.value = f.id;
  editName.value = f.name;
  editDesc.value = f.description || "";
}

async function saveEdit() {
  const name = editName.value.trim();
  if (!name) return;
  saving.value = true;
  try {
    await families.update(editingId.value, { name, description: editDesc.value.trim() || null });
    editingId.value = null;
    toast("Family updated", "success");
  } catch (e) {
    toast(e.message, "error");
  } finally {
    saving.value = false;
  }
}

function cancelEdit() {
  editingId.value = null;
}

function onAvatarFile(f, e) {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    toast("Please choose an image file", "error");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    toast("Image too large (max 10 MB)", "error");
    return;
  }
  uploadingFor.value = f.id;
  families
    .uploadAvatar(f.id, file)
    .then(() => toast("Family photo updated", "success"))
    .catch((err) => toast(err.message, "error"))
    .finally(() => {
      uploadingFor.value = null;
    });
}

async function remove(f) {
  if (!confirm(`Delete family "${f.name}"? This will also unassign any pending invites that point at it.`)) return;
  try {
    await families.remove(f.id);
    toast("Family deleted", "success");
  } catch (e) {
    toast(e.message, "error");
  }
}
</script>

<template>
  <div class="families-layout">
    <Sidebar :mobile-open="mobileSidebar" @close="mobileSidebar = false" />

    <section class="families-main">
      <header class="page-header">
        <button class="mobile-toggle" @click="mobileSidebar = true">☰</button>
        <h1>Families</h1>
        <span class="count">{{ families.families.length }} famil{{ families.families.length === 1 ? "y" : "ies" }}</span>
      </header>

      <p class="page-hint">
        Group members into families. When you send an invite, choose which family the new member
        joins — they're added to it automatically.
      </p>

      <!-- Create -->
      <div class="card create-card">
        <h2>New family</h2>
        <div class="create-row">
          <input v-model="newName" placeholder="e.g. Holsapples" maxlength="80" class="name-input" />
          <input v-model="newDesc" placeholder="Description (optional)" maxlength="280" class="desc-input" />
          <button class="btn" :disabled="creating || !newName.trim()" @click="create">
            {{ creating ? "Creating…" : "Create" }}
          </button>
        </div>
      </div>

      <!-- List -->
      <div v-if="families.families.length === 0" class="empty-state">
        <div class="empty-icon">🏠</div>
        <h2>No families yet</h2>
        <p>Create your first family above, then invite people into it.</p>
      </div>

      <div v-else class="family-list">
        <div v-for="f in families.families" :key="f.id" class="family-card card">
          <div v-if="editingId === f.id" class="edit-row">
            <input v-model="editName" maxlength="80" class="name-input" />
            <input v-model="editDesc" maxlength="280" class="desc-input" />
            <div class="edit-actions">
              <button class="btn btn-sm" :disabled="saving" @click="saveEdit">Save</button>
              <button class="btn btn-ghost btn-sm" @click="cancelEdit">Cancel</button>
            </div>
          </div>
          <div v-else class="family-body">
            <label class="family-avatar-wrap">
              <input
                type="file"
                accept="image/*"
                style="display: none"
                @change="onAvatarFile(f, $event)"
              />
              <div class="family-avatar">
                <img v-if="f.avatar_url" :src="f.avatar_url" :alt="f.name" />
                <span v-else class="avatar-placeholder">🏠</span>
                <span class="avatar-hint">
                  {{ uploadingFor === f.id ? "Uploading…" : f.avatar_url ? "Change" : "Add" }}
                </span>
              </div>
            </label>
            <div class="family-info">
              <div class="family-name">{{ f.name }}</div>
              <div v-if="f.description" class="family-desc">{{ f.description }}</div>
              <div class="family-meta">{{ f.member_count }} member{{ f.member_count === 1 ? "" : "s" }}</div>
            </div>
            <div class="family-actions">
              <button class="btn btn-ghost btn-sm" @click="startEdit(f)">Edit</button>
              <button class="btn btn-ghost btn-sm danger-text" @click="remove(f)">Delete</button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.families-layout { flex: 1; display: flex; overflow: hidden; }
.families-main { flex: 1; overflow-y: auto; padding: 20px; }
.page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.page-header h1 { font-size: 22px; }
.count { color: var(--text-muted); font-size: 14px; margin-left: auto; }
.mobile-toggle { display: none; }
.page-hint { color: var(--text-muted); font-size: 13px; margin-bottom: 20px; max-width: 640px; line-height: 1.5; }
.create-card { max-width: 640px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 14px; }
.create-card h2 { font-size: 16px; }
.create-row { display: flex; gap: 10px; align-items: center; }
.name-input { flex: 0 0 200px; }
.desc-input { flex: 1; }
.empty-state { text-align: center; color: var(--text-muted); padding: 60px 20px; }
.empty-icon { font-size: 56px; margin-bottom: 16px; }
.empty-state h2 { color: var(--text); margin-bottom: 8px; }
.family-list { display: flex; flex-direction: column; gap: 12px; max-width: 640px; }
.family-card { padding: 16px; }
.family-body { display: flex; align-items: center; gap: 16px; }
.family-avatar-wrap {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
  display: inline-block;
}
.family-avatar {
  width: 64px;
  height: 64px;
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  border: 1px solid var(--border);
  transition: border-color 0.15s;
}
.family-avatar-wrap:hover .family-avatar { border-color: var(--accent); }
.family-avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-placeholder { font-size: 28px; }
.avatar-hint {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}
.family-avatar-wrap:hover .avatar-hint { opacity: 1; }
.family-info { flex: 1; min-width: 0; }
.family-name { font-weight: 600; font-size: 16px; }
.family-desc { font-size: 13px; color: var(--text-muted); margin-top: 4px; white-space: pre-wrap; }
.family-meta { font-size: 12px; color: var(--text-muted); margin-top: 6px; }
.family-actions { display: flex; gap: 8px; }
.edit-row { display: flex; flex-direction: column; gap: 10px; }
.edit-actions { display: flex; gap: 8px; }
.danger-text { color: var(--danger); }

@media (max-width: 768px) {
  .mobile-toggle { display: inline-block; font-size: 18px; color: var(--text); }
  .create-row { flex-wrap: wrap; }
  .name-input, .desc-input { flex: 1 1 100%; }
  .family-body { flex-direction: column; align-items: flex-start; }
}
</style>
