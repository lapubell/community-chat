import { defineStore } from "pinia";
import { api } from "@/api";

export const useFamiliesStore = defineStore("families", {
  state: () => ({
    families: [],
    loaded: false,
  }),
  getters: {
    byId: (s) => (id) => s.families.find((f) => f.id === id) || null,
  },
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return;
      this.families = await api.get("/api/families");
      this.loaded = true;
    },
    async create({ name, description }) {
      const family = await api.post("/api/families", { name, description });
      this.families.push(family);
      this.families.sort((a, b) => a.name.localeCompare(b.name));
      return family;
    },
    async update(id, { name, description }) {
      const family = await api.put(`/api/families/${id}`, { name, description });
      const idx = this.families.findIndex((f) => f.id === id);
      if (idx >= 0) this.families.splice(idx, 1, family);
      this.families.sort((a, b) => a.name.localeCompare(b.name));
      return family;
    },
    async remove(id) {
      await api.del(`/api/families/${id}`);
      this.families = this.families.filter((f) => f.id !== id);
    },
    async uploadAvatar(id, file) {
      const fd = new FormData();
      fd.append("file", file);
      const family = await api.upload(`/api/families/${id}/avatar`, fd);
      const idx = this.families.findIndex((f) => f.id === id);
      if (idx >= 0) this.families.splice(idx, 1, family);
      return family;
    },
  },
});
