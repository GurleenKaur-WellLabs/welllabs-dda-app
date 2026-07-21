<script>
	import { goto } from '$app/navigation';
	import { session } from '$lib/shared/session.svelte.js';
	import DashboardHeader from '$lib/shared/components/landing/DashboardHeader.svelte';
	import ContourBackground from '$lib/shared/components/landing/ContourBackground.svelte';

	const modules = [
		{
			id: 'diagnose',
			href: '/diagnose',
			title: 'Diagnose',
			description:
				'Map watersheds, draw observation zones, and capture geotagged field notes — synced offline with QField.',
			status: 'Available',
			accent: '#4FD1C5',
			accentClass: 'text-diagnose',
			borderClass: 'hover:border-diagnose/40',
			badgeClass: 'text-diagnose border-diagnose/30 bg-diagnose/10',
			icon: 'diagnose'
		},
		{
			id: 'design',
			href: '/design',
			title: 'Design',
			description: 'Plan and design interventions on top of diagnosed watersheds.',
			status: 'Coming soon',
			accent: '#E8B75A',
			accentClass: 'text-design',
			borderClass: 'hover:border-design/40',
			badgeClass: 'text-design border-design/30 bg-design/10',
			icon: 'design'
		},
		{
			id: 'assess',
			href: '/assess',
			title: 'Assess',
			description: 'Track outcomes and assess impact of implemented designs over time.',
			status: 'Coming soon',
			accent: '#A78BFA',
			accentClass: 'text-assess',
			borderClass: 'hover:border-assess/40',
			badgeClass: 'text-assess border-assess/30 bg-assess/10',
			icon: 'assess'
		}
	];

	function openModule(mod) {
		goto(mod.href);
	}
</script>

<svelte:head>
	<title>Dashboard · DDA</title>
</svelte:head>

<div class="relative min-h-screen bg-void font-body">
	<ContourBackground intensity="ambient" />
	<DashboardHeader name={session.user?.name ?? ''} />

	<main class="relative z-10 px-6 py-14 md:px-10">
		<div class="mx-auto max-w-6xl">
			<span class="font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">Where you left off</span>
			<h1 class="mt-2 font-display text-3xl text-ink md:text-4xl">
				Welcome, {session.user?.name ?? ''}.
			</h1>
			<p class="mt-3 max-w-xl font-body text-[14px] leading-relaxed text-ink-dim">
				Pick a module below to get started, or continue where you left off.
			</p>

			<h2 class="mt-12 mb-5 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-faint">
				Choose a module
			</h2>

			<div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 mt-2">
				{#each modules as mod (mod.id)}
					<button
						type="button"
						class="group flex flex-col items-start gap-3 rounded-[20px] border border-hairline bg-panel p-6 text-left shadow-glass transition-all duration-300 hover:-translate-y-1 {mod.borderClass}"
						onclick={() => openModule(mod)}
					>
						<div
							class="flex h-12 w-12 items-center justify-center rounded-xl border border-hairline"
							style:background-color="color-mix(in srgb, {mod.accent} 14%, transparent)"
						>
							{#if mod.icon === 'diagnose'}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke={mod.accent} stroke-width="1.75" class="h-6 w-6">
									<circle cx="12" cy="12" r="7.5" />
									<path d="M12 4.5v15M4.5 12h15" />
									<circle cx="12" cy="12" r="1.75" fill={mod.accent} stroke="none" />
								</svg>
							{:else if mod.icon === 'design'}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke={mod.accent} stroke-width="1.75" class="h-6 w-6">
									<path d="M4 19.5V16l9-9 3.5 3.5-9 9H4z" stroke-linejoin="round" />
									<path d="M13 7l3.5 3.5" />
									<path d="M17.5 4.5 19.5 6.5" stroke-linecap="round" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke={mod.accent} stroke-width="1.75" class="h-6 w-6">
									<path d="M4 19h16" stroke-linecap="round" />
									<path d="M7 19v-5M12 19V8M17 19v-9" stroke-linecap="round" />
								</svg>
							{/if}
						</div>

						<div class="flex w-full items-center justify-between gap-2">
							<h3 class="m-0 font-display text-lg text-ink">{mod.title}</h3>
							<span class="shrink-0 rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide {mod.badgeClass}">
								{mod.status}
							</span>
						</div>

						<p class="m-0 font-body text-[13px] leading-relaxed text-ink-dim">{mod.description}</p>

						<span class="mt-1 inline-flex items-center gap-1 font-mono text-[12px] {mod.accentClass}">
							Open {mod.title}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5">
								<path d="M5 12h14M13 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
							</svg>
						</span>
					</button>
				{/each}
			</div>
		</div>
	</main>
</div>