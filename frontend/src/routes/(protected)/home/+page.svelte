<script>
	import { goto } from '$app/navigation';
	import { session } from '$lib/shared/session.svelte.js';
	import UserMenu from '$lib/shared/components/UserMenu.svelte';

	const modules = [
		{
			id: 'diagnose',
			href: '/diagnose',
			title: 'Diagnose',
			description:
				'Map watersheds, draw observation zones, and capture geotagged field notes — synced offline with QField.',
			status: 'Available',
			available: true,
			accent: '#1b75e0',
			icon: 'diagnose'
		},
		{
			id: 'design',
			href: '/design',
			title: 'Design',
			description: 'Plan and design interventions on top of diagnosed watersheds.',
			status: 'Coming soon',
			available: true,
			accent: '#0d983b',
			icon: 'design'
		},
		{
			id: 'assess',
			href: '/assess',
			title: 'Assess',
			description: 'Track outcomes and assess impact of implemented designs over time.',
			status: 'Coming soon',
			available: true,
			accent: '#d5b443',
			icon: 'assess'
		}
	];

	function openModule(mod) {
		goto(mod.href);
	}
</script>

<svelte:head>
	<title>Dashboard · DDA Product</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-white font-body">
	<header class="border-b border-brand-navy/20 bg-brand-navy px-6 py-10 text-white">
		<div class="mx-auto flex max-w-5xl items-start justify-between gap-4">
			<div>
				<h1 class="m-0 font-headline text-3xl font-semibold">
					Welcome, {session.user?.name ?? ''}
				</h1>
				<p class="m-0 mt-2 max-w-xl font-body text-sm text-brand-sky/90">
					Pick a module below to get started, or continue where you left off.
				</p>
			</div>
			<div class="shrink-0 pt-1">
				<UserMenu />
			</div>
		</div>
	</header>

	<main class="flex-1 px-6 py-10">
		<div class="mx-auto max-w-5xl">
			<h2 class="m-0 mb-5 font-headline text-sm font-semibold tracking-wide text-brand-navy/60 uppercase">
				Choose a module
			</h2>
			<div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
				{#each modules as mod (mod.id)}
					<button
						type="button"
						class="group flex cursor-pointer flex-col items-start gap-3 rounded-2xl border border-brand-navy/10 bg-white p-6 text-left shadow-sm transition-shadow hover:shadow-md"
						onclick={() => openModule(mod)}
					>
						<div
							class="flex h-12 w-12 items-center justify-center rounded-xl"
							style:background-color="color-mix(in srgb, {mod.accent} 16%, transparent)"
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
							<h3 class="m-0 font-headline text-lg font-semibold text-brand-navy">{mod.title}</h3>
							<span
								class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase"
								style:background-color="color-mix(in srgb, {mod.accent} 16%, transparent)"
								style:color={mod.accent}
							>
								{mod.status}
							</span>
						</div>

						<p class="m-0 text-sm leading-relaxed text-brand-steel">{mod.description}</p>

						<span
							class="mt-1 inline-flex items-center gap-1 font-body text-sm font-medium"
							style:color={mod.accent}
						>
							Open {mod.title}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 transition-transform group-hover:translate-x-0.5">
								<path d="M5 12h14M13 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
							</svg>
						</span>
					</button>
				{/each}
			</div>
		</div>
	</main>
</div>
