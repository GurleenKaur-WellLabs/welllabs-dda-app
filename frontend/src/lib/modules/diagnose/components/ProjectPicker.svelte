<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import ModuleHeader from '$lib/shared/components/ModuleHeader.svelte';
	import LocationPicker from '$lib/shared/components/LocationPicker.svelte';
	import WatershedThumb from '$lib/shared/components/WatershedThumb.svelte';
	import { itemPath } from '$lib/shared/slug.js';
	import { session } from '$lib/shared/session.svelte.js';
	import FieldNoteIcon from '$lib/modules/diagnose/components/icons/FieldNoteIcon.svelte';
	import ObservationZoneIcon from '$lib/modules/diagnose/components/icons/ObservationZoneIcon.svelte';
	import { createProject, deleteProject, fetchProjects, lookupWatershed } from '$lib/modules/diagnose/api';

	let projects = $state([]);
	let loading = $state(true);
	let error = $state('');
	let showCreate = $state(false);
	let openMenuId = $state(null);
	let name = $state('');
	let lng = $state(77.2);
	let lat = $state(28.6);
	let watershedPreview = $state(null);
	let previewLoading = $state(false);
	let creating = $state(false);
	let deletingId = $state(null);

	onMount(() => {
		loadProjects();
		document.addEventListener('click', closeMenu);
		return () => document.removeEventListener('click', closeMenu);
	});

	function closeMenu() {
		openMenuId = null;
	}

	async function loadProjects() {
		loading = true;
		error = '';
		try {
			const data = await fetchProjects();
			projects = data.projects ?? [];
		} catch (err) {
			error = String(err);
		} finally {
			loading = false;
		}
	}

	async function previewWatershed() {
		previewLoading = true;
		watershedPreview = null;
		try {
			watershedPreview = await lookupWatershed(lng, lat);
		} catch (err) {
			watershedPreview = { error: String(err) };
		} finally {
			previewLoading = false;
		}
	}

	function openProject(project) {
		goto(itemPath('/diagnose', project, projects));
	}

	async function handleCreate() {
		if (!name.trim()) return;
		creating = true;
		error = '';
		try {
			const project = await createProject(name.trim(), lng, lat);
			showCreate = false;
			name = '';
			watershedPreview = null;
			await loadProjects();
			openProject(project);
		} catch (err) {
			error = String(err);
		} finally {
			creating = false;
		}
	}

	function openCreate() {
		showCreate = true;
		error = '';
		watershedPreview = null;
	}

	function formatProjectDate(iso) {
		const d = new Date(iso);
		const day = d.getDate();
		const suffix =
			day % 10 === 1 && day !== 11
				? 'st'
				: day % 10 === 2 && day !== 12
					? 'nd'
					: day % 10 === 3 && day !== 13
						? 'rd'
						: 'th';
		const monthYear = d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
		return `${day}${suffix} ${monthYear}`;
	}

	function toggleMenu(e, projectId) {
		e.stopPropagation();
		openMenuId = openMenuId === projectId ? null : projectId;
	}

	function isOwner(project) {
		return session.user && project.owner_id === session.user.id;
	}

	function handleManageMembers(e, project) {
		e.stopPropagation();
		openMenuId = null;
		goto(`${itemPath('/diagnose', project, projects)}/members`);
	}

	async function handleDeleteProject(e, project) {
		e.stopPropagation();
		openMenuId = null;
		if (!confirm(`Delete project "${project.name}"? This cannot be undone.`)) return;
		deletingId = project.id;
		error = '';
		try {
			await deleteProject(project.id);
			await loadProjects();
		} catch (err) {
			error = String(err);
		} finally {
			deletingId = null;
		}
	}
</script>

<div class="relative min-h-screen bg-transparent font-body">
	<ModuleHeader title="Diagnose" subtitle="Select a project or create a new one to begin mapping." />

	<main class="relative z-10 flex-1 overflow-auto p-6">
		{#if loading}
			<p class="text-brand-steel">Loading projects…</p>
		{:else if showCreate}
			<div class="mx-auto max-w-2xl rounded-xl bg-white p-6 shadow-sm">
				<h2 class="m-0 mb-4 font-headline text-lg font-semibold text-brand-navy">New project</h2>

				<label class="mb-1 block font-body text-sm font-medium text-brand-navy" for="proj-name"
					>Project name</label
				>
				<input
					id="proj-name"
					type="text"
					class="mb-4 w-full rounded border border-brand-navy/20 px-3 py-2 font-body"
					bind:value={name}
					placeholder="e.g. North basin survey"
				/>

				<div class="mb-4 h-80">
					<LocationPicker bind:lng bind:lat onPick={previewWatershed} />
				</div>

				<div class="mb-4 rounded-lg bg-brand-sky/20 p-3 font-body text-sm">
					{#if previewLoading}
						<p class="m-0 text-brand-steel">Looking up watershed…</p>
					{:else if watershedPreview?.error}
						<p class="m-0 text-red-600">{watershedPreview.error}</p>
					{:else if watershedPreview}
						<p class="m-0 font-medium text-brand-navy">Watershed: {watershedPreview.watershed_name}</p>
						<p class="m-0 mt-1 text-brand-steel">ID: {watershedPreview.watershed_id}</p>
					{:else}
						<p class="m-0 text-brand-steel">
							Click the map to detect the watershed at that location.
						</p>
					{/if}
				</div>

				{#if error}
					<p class="mb-3 text-sm text-red-600">{error}</p>
				{/if}

				<div class="flex gap-2">
					<button
						class="cursor-pointer rounded bg-brand-blue px-4 py-2 font-body text-white disabled:opacity-60"
						disabled={creating || !name.trim()}
						onclick={handleCreate}
					>
						{creating ? 'Creating…' : 'Create project'}
					</button>
					<button
						class="cursor-pointer rounded bg-brand-steel px-4 py-2 font-body text-white hover:bg-brand-navy"
						onclick={() => (showCreate = false)}
					>
						Cancel
					</button>
				</div>
			</div>
		{:else}
			{#if error}
				<p class="mb-4 text-sm text-red-600">{error}</p>
			{/if}

			<div
				class="grid gap-5"
				style="grid-template-columns: repeat(auto-fill, minmax(min(100%, 20rem), 1fr));"
			>
				<button
					class="flex min-h-[7rem] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-brand-blue/50 bg-white p-4 text-brand-blue shadow-sm hover:border-brand-blue hover:bg-brand-sky/15"
					onclick={openCreate}
				>
					<span class="font-headline text-3xl leading-none">+</span>
					<span class="mt-2 font-body font-medium">New project</span>
				</button>

				{#each projects as project (project.id)}
					<div
						class="relative flex cursor-pointer flex-col rounded-2xl border border-brand-navy/10 bg-white shadow-sm transition-shadow hover:border-brand-blue/30 hover:shadow-md"
						role="button"
						tabindex="0"
						onclick={() => openProject(project)}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								openProject(project);
							}
						}}
					>
						<div class="relative flex items-center gap-3 p-3 pr-10">
							<div class="h-16 w-16 shrink-0">
								<WatershedThumb geometry={project.watershed_geometry} circular />
							</div>

							<h3
								class="m-0 min-w-0 flex-1 break-words font-headline text-lg font-semibold tracking-tight text-brand-navy"
							>
								{project.name}
							</h3>

							<div class="absolute top-2 right-2">
								<button
									type="button"
									class="flex h-7 w-7 cursor-pointer items-center justify-center rounded border-0 bg-transparent text-brand-steel hover:bg-brand-sky/20 hover:text-brand-navy"
									aria-label="Project actions"
									disabled={deletingId === project.id}
									onclick={(e) => toggleMenu(e, project.id)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 24 24"
										fill="currentColor"
										class="h-5 w-5"
									>
										<circle cx="12" cy="5" r="1.5" />
										<circle cx="12" cy="12" r="1.5" />
										<circle cx="12" cy="19" r="1.5" />
									</svg>
								</button>
								{#if openMenuId === project.id}
									<div
										class="absolute right-0 z-20 mt-1 min-w-32 overflow-hidden rounded border border-brand-navy/10 bg-white shadow-lg"
									>
										{#if isOwner(project)}
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left font-body text-sm text-brand-navy hover:bg-brand-sky/15"
												onclick={(e) => handleManageMembers(e, project)}
											>
												Members
											</button>
											<button
												type="button"
												class="block w-full cursor-pointer border-0 bg-white px-3 py-2 text-left font-body text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
												disabled={deletingId === project.id}
												onclick={(e) => handleDeleteProject(e, project)}
											>
												{deletingId === project.id ? 'Deleting…' : 'Delete'}
											</button>
										{:else}
											<p class="m-0 px-3 py-2 text-left font-body text-xs text-brand-steel">
												Shared with you
											</p>
										{/if}
									</div>
								{/if}
							</div>
						</div>

						<div
							class="flex items-center justify-between gap-3 border-t border-brand-navy/10 bg-gray-50 px-3 py-2"
						>
							<div class="flex min-w-0 items-center gap-2">
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									class="h-3.5 w-3.5 shrink-0 text-brand-steel"
									aria-hidden="true"
								>
									<rect x="3" y="5" width="18" height="16" rx="2" />
									<path d="M8 3v4M16 3v4M3 10h18" stroke-linecap="round" />
								</svg>
								<p
									class="m-0 font-body text-[9px] leading-snug font-medium tracking-wide text-brand-steel"
								>
									{formatProjectDate(project.updated_at ?? project.created_at)}
								</p>
							</div>

							<div class="flex shrink-0 items-center gap-3">
								<div
									class="flex items-center gap-1.5"
									aria-label="{project.observation_zone_count ?? 0} observation zones"
								>
									<ObservationZoneIcon size="sm" />
									<span class="font-headline text-sm leading-none font-medium text-brand-navy">
										{project.observation_zone_count ?? 0}
									</span>
								</div>

								<div class="h-5 w-px shrink-0 bg-brand-navy/10" aria-hidden="true"></div>

								<div
									class="flex items-center gap-1.5"
									aria-label="{project.field_note_count ?? 0} field notes"
								>
									<FieldNoteIcon size="sm" />
									<span class="font-headline text-sm leading-none font-medium text-brand-navy">
										{project.field_note_count ?? 0}
									</span>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>

			{#if projects.length === 0}
				<p class="mt-4 font-body text-sm text-brand-steel">No projects yet. Create one to get started.</p>
			{/if}
		{/if}
	</main>
</div>
