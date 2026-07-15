<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { session } from '$lib/shared/session.svelte.js';

	let { children } = $props();

	const navItems = [
		{ href: '/settings', label: 'Account' },
		{ href: '/settings/organizations', label: 'Organizations' },
		{ href: '/settings/connectors', label: 'Connectors' }
	];

	function isActive(href) {
		if (href === '/settings') return page.url.pathname === '/settings';
		return page.url.pathname.startsWith(href);
	}

	async function handleLogout() {
		await session.logout();
		goto('/');
	}
</script>

<div class="flex min-h-screen flex-col bg-gray-50 font-body">
	<header class="flex items-center justify-between border-b border-brand-navy/20 bg-brand-navy px-6 py-4 text-white">
		<div class="flex items-center gap-3">
			<button
				class="cursor-pointer rounded border border-brand-sky/40 bg-transparent px-2 py-1 font-body text-sm text-white hover:bg-white/10"
				onclick={() => goto('/home')}
			>
				← Home
			</button>
			<h1 class="m-0 font-headline text-xl font-semibold">Settings</h1>
		</div>
		{#if session.user}
			<div class="flex items-center gap-2">
				<span
					class="flex h-7 w-7 items-center justify-center rounded-full bg-brand-blue text-xs font-semibold text-white"
				>
					{(session.user.name ?? '?').charAt(0).toUpperCase()}
				</span>
				<span class="font-body text-sm font-medium">{session.user.name}</span>
			</div>
		{/if}
	</header>

	<div class="mx-auto flex w-full max-w-5xl flex-1 gap-0">
		<nav class="w-56 shrink-0 border-r border-brand-navy/8 bg-white py-4 pr-2 pl-4">
			<ul class="m-0 flex flex-col gap-0.5 p-0">
				{#each navItems as item (item.href)}
					<li>
						<a
							href={item.href}
							class="block rounded-lg px-3 py-2 font-body text-sm font-medium no-underline transition-colors {isActive(item.href)
								? 'bg-brand-sky/15 text-brand-navy'
								: 'text-brand-steel hover:bg-gray-50 hover:text-brand-navy'}"
						>
							{item.label}
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<main class="flex-1 overflow-auto p-6">
			{@render children?.()}
		</main>
	</div>
</div>
