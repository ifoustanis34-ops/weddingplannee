<script setup lang="ts">
/**
 * Design system gallery (complement, step B): every W* component in both themes, side by side.
 * Development tool only (route registered when `import.meta.env.DEV`); sample values are
 * illustrative and never reach the product screens.
 */
import { Download, FileText, PackageSearch, Plus, Search, Trash2 } from '@lucide/vue'
import { ref } from 'vue'

import { formatMoneyShort } from '@/composables/useMoney'
import { useToast } from '@/composables/useToast'
import {
  type Channel,
  type TableColumn,
  WAlert,
  WAreaChart,
  WAvatar,
  WBadge,
  WButton,
  WCard,
  WChannelIcon,
  WChips,
  WDateBlock,
  WDrawer,
  WEmptyState,
  WInput,
  WLogo,
  WModal,
  WMoney,
  WNote,
  WPhaseTag,
  WProgress,
  WRibbons,
  WSelect,
  WSwitch,
  WTable,
  WTabs,
  WTextarea,
  WTile,
} from '@/design'

const toast = useToast()
const themes = ['light', 'dark'] as const

const text = ref('Maison Élégance Events')
const slug = ref('maison-elegance')
const discount = ref<string | number | null>(10)
const select = ref<string | number | null>('whatsapp')
const notes = ref('Mariage civil + réception 180 invités, thème ivoire et or')
const enabled = ref(true)
const disabled = ref(false)
const tab = ref('all')
const chip = ref('all')
const drawerOpen = ref(false)
const modalOpen = ref(false)

const sources = [
  { value: 'furniture', label: 'Mobilier' },
  { value: 'linen', label: 'Linge de table' },
  { value: 'lighting', label: 'Éclairage' },
]
const tabs = [
  { key: 'all', label: 'Tous', count: 8 },
  { key: 'draft', label: 'Brouillons', count: 1 },
  { key: 'sent', label: 'Envoyés', count: 3 },
]
const chips = [
  { value: 'all', label: 'Tous' },
  { value: 'coordination', label: 'Coordination' },
  { value: 'decoration', label: 'Décoration' },
]
const tones = ['violet', 'fuchsia', 'coral', 'gold', 'green', 'red', 'grey'] as const
const channels: Channel[] = ['email', 'call', 'whatsapp', 'task']
const cashflow = [
  { label: 'mai', value: 3_200_000 },
  { label: 'juin', value: 4_100_000 },
  { label: 'juil.', value: 2_800_000 },
  { label: 'août', value: 5_600_000 },
  { label: 'sept.', value: 4_900_000 },
  { label: 'oct.', value: 6_300_000 },
]
const formatTick = (value: number) => (value === 0 ? '0' : String(value / 1_000_000))
const columns: TableColumn[] = [
  { key: 'number', label: 'Numéro' },
  { key: 'client', label: 'Client' },
  { key: 'total', label: 'Montant', align: 'right' },
]
const rows = [
  { id: '1', number: 'DV-2026-0047', client: 'Patricia Ouattara', total: 4_350_000 },
  { id: '2', number: 'DV-2026-0046', client: 'Yannick Touré', total: 2_140_000 },
]
</script>

<template>
  <div class="grid min-h-dvh xl:grid-cols-2">
    <section
      v-for="theme in themes"
      :key="theme"
      :class="`theme-${theme}`"
      class="flex min-w-0 flex-col gap-6 bg-bg p-4 text-ink sm:p-6"
      :aria-label="theme === 'light' ? 'Thème clair' : 'Thème sombre'"
    >
      <header class="flex items-center gap-4">
        <WLogo />
        <WPhaseTag>{{ theme === 'light' ? 'Clair' : 'Sombre' }}</WPhaseTag>
      </header>

      <WCard title="Boutons" subtitle="primary, secondary, ghost, danger · md, sm, icon">
        <div class="flex flex-wrap items-center gap-2">
          <WButton><FileText class="size-[18px]" aria-hidden="true" />Créer un devis</WButton>
          <WButton variant="secondary"
            ><Plus class="size-[18px]" aria-hidden="true" />Nouveau client</WButton
          >
          <WButton variant="ghost">Annuler</WButton>
          <WButton variant="danger">Supprimer</WButton>
          <WButton loading>Envoi…</WButton>
          <WButton disabled>Désactivé</WButton>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-2">
          <WButton size="sm">Marquer faite</WButton>
          <WButton size="sm" variant="secondary"
            ><Download class="size-[15px]" aria-hidden="true" />Exporter</WButton
          >
          <WButton icon variant="secondary" aria-label="Rechercher"
            ><Search class="size-[18px]" aria-hidden="true"
          /></WButton>
          <WButton icon size="sm" variant="ghost" aria-label="Supprimer"
            ><Trash2 class="size-[15px]" aria-hidden="true"
          /></WButton>
        </div>
      </WCard>

      <WCard title="Champs" subtitle="Hauteur 42, focus violet et halo, groupe avec suffixe">
        <div class="grid gap-4 sm:grid-cols-2">
          <WInput
            v-model="text"
            label="Nom de l’entreprise"
            placeholder="Ex. Maison Élégance Events"
          />
          <WInput
            v-model="slug"
            label="Adresse de votre espace"
            addon=".wedivo.pro"
            hint="Vos clients et votre équipe se connectent à cette adresse."
          />
          <WInput v-model="discount" label="Remise" type="number" addon="%" />
          <WInput
            model-value="awa@"
            label="Email professionnel"
            error="Cette adresse email n’est pas valide."
          />
          <WSelect v-model="select" label="Catégorie" :options="sources" />
          <WTextarea v-model="notes" label="Préférences" />
        </div>
      </WCard>

      <WCard title="Interrupteurs, badges, étiquettes">
        <div class="flex flex-col gap-4">
          <WSwitch
            v-model="enabled"
            label="Résumé quotidien des alertes"
            description="Email au propriétaire chaque matin : stock bas, retours en retard."
          />
          <WSwitch
            v-model="disabled"
            label="WhatsApp Business"
            description="Connexion requise"
            disabled
          />
          <div class="flex flex-wrap gap-2">
            <WBadge v-for="tone in tones" :key="tone" :tone="tone">{{ tone }}</WBadge>
          </div>
          <div class="flex flex-wrap gap-2">
            <WPhaseTag>P2</WPhaseTag>
            <WPhaseTag>Phase 3</WPhaseTag>
          </div>
        </div>
      </WCard>

      <div class="grid grid-cols-2 gap-3.5">
        <WTile dark label="Temps moyen de création" value="18 min" />
        <WTile label="Envoyés ce mois" value="12" />
        <WTile label="Taux d’acceptation" value="64 %" />
        <WTile label="Montant en attente"
          ><template #value><WMoney :amount="9_350_000" /></template
        ></WTile>
      </div>

      <WCard title="Encaissements" subtitle="Six derniers mois, en millions de FCFA">
        <WAreaChart
          :points="cashflow"
          label="Encaissements par mois"
          :format-tick="formatTick"
          :format-value="formatMoneyShort"
        />
      </WCard>

      <WCard title="Onglets, puces, tableau">
        <WTabs v-model="tab" :tabs="tabs" label="Devis">
          <WChips v-model="chip" :options="chips" label="Catégories" class="mb-4" />
          <WTable :columns="columns" :rows="rows" row-key="id" caption="Devis" clickable-rows>
            <template #cell-total="{ value }"><WMoney :amount="value as number" /></template>
          </WTable>
        </WTabs>
      </WCard>

      <WCard title="Progression, dates, canaux, avatars">
        <div class="flex flex-col gap-4">
          <WProgress :value="62" label="Avancement" show-value />
          <WProgress :value="75" label="Préparation" ribbon show-value />
          <div class="flex flex-wrap items-center gap-3">
            <WDateBlock date="2026-10-31" />
            <WDateBlock date="2026-11-14" weekday />
            <WChannelIcon
              v-for="channel in channels"
              :key="channel"
              :channel="channel"
              :label="channel"
            />
            <WAvatar name="Freddy Kouamé" />
            <WAvatar name="Aïcha & Serge Kouassi" :size="44" />
            <WAvatar name="Maison Élégance Events" kind="organization" />
          </div>
        </div>
      </WCard>

      <WNote
        >La marge prévisionnelle compare le contrat aux dépenses saisies pour ce mariage.</WNote
      >
      <WAlert
        title="Chaise Chiavari : 280 demandées pour 250 en stock"
        text="Réservation du 22 nov. : proposez des chaises Napoléon ou une location complémentaire."
      >
        <WButton size="sm"
          ><PackageSearch class="size-[15px]" aria-hidden="true" />Voir les équivalents</WButton
        >
      </WAlert>
      <WEmptyState title="Aucun devis dans cette catégorie." />

      <div class="relative h-40 overflow-hidden rounded-[22px] bg-hero p-6">
        <WRibbons class="pointer-events-none absolute -top-10 -right-[70px] w-[340px]" />
        <WLogo inverse class="relative" />
      </div>

      <div class="flex flex-wrap gap-2">
        <WButton variant="secondary" @click="drawerOpen = true">Ouvrir le tiroir</WButton>
        <WButton variant="secondary" @click="modalOpen = true">Ouvrir la modale</WButton>
        <WButton variant="secondary" @click="toast.success('Paiement de 500 000 FCFA enregistré')"
          >Toast</WButton
        >
        <WButton
          variant="secondary"
          @click="toast.error('Indiquez le nom du client avant de continuer.')"
          >Toast d’erreur</WButton
        >
      </div>
    </section>

    <WDrawer
      v-model:open="drawerOpen"
      title="Mariage de Mariam & Idriss"
      subtitle="Sofitel Hôtel Ivoire, 320 invités"
    >
      <WNote>Le tiroir et la modale suivent le thème de la page.</WNote>
      <template #footer
        ><WButton variant="secondary" @click="drawerOpen = false">Fermer</WButton></template
      >
    </WDrawer>
    <WModal v-model:open="modalOpen" title="Nouveau client">
      <WInput v-model="text" label="Nom ou couple" />
      <template #footer>
        <WButton variant="secondary" @click="modalOpen = false">Annuler</WButton>
        <WButton @click="modalOpen = false">Ajouter le client</WButton>
      </template>
    </WModal>
  </div>
</template>
