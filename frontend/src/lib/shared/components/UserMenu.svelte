<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { session } from '$lib/shared/session.svelte.js';

	let open = $state(false);
	let menuEl = $state(null);

	function toggle() {
		open = !open;
	}

	function close(e) {
		if (menuEl && !menuEl.contains(e.target)) {
			open = false;
		}
	}

	onMount(() => {
		document.addEventListener('click', close, true);
		return () => document.removeEventListener('click', close, true);
	});

	function nav(path) {
		open = false;
		goto(path);
	}

	async function handleSignOut() {
		open = false;
		await session.logout();
		goto('/');
	}
</script>

{#if session.user}
	<div class="relative" bind:this={menuEl}>
		<button
			type="button"
			class="flex cursor-pointer items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-2.5 py-1.5 text-white hover:bg-white/20"
			onclick={toggle}
		>
			<span
				class="flex h-7 w-7 items-center justify-center rounded-full bg-brand-blue text-xs font-semibold text-white"
			>
				{(session.user.name ?? '?').charAt(0).toUpperCase()}
			</span>
			<span class="font-body text-sm font-medium">{session.user.name}</span>
			<svg
				xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"
				class="h-4 w-4 opacity-70 transition-transform {open ? 'rotate-180' : ''}"
			>
				<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
			</svg>
		</button>

		{#if open}
			<div class="absolute right-0 z-50 mt-1.5 min-w-48 overflow-hidden rounded-lg border border-brand-navy/10 bg-white shadow-lg">
				<button
					type="button"
					class="flex w-full cursor-pointer items-center gap-2.5 border-0 bg-white px-4 py-2.5 text-left font-body text-sm text-brand-navy hover:bg-gray-50"
					onclick={() => nav('/settings/organizations')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4 text-brand-steel">
						<path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
					</svg>
					Organizations
				</button>
				<button
					type="button"
					class="flex w-full cursor-pointer items-center gap-2.5 border-0 bg-white px-4 py-2.5 text-left font-body text-sm text-brand-navy hover:bg-gray-50"
					onclick={() => nav('/settings/connectors')}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4 text-brand-steel">
						<path fill-rule="evenodd" d="M1 2.75A.75.75 0 011.75 2h16.5a.75.75 0 010 1.5H18v8.75A2.75 2.75 0 0115.25 15h-1.072l.798 3.06a.75.75 0 01-1.452.38L13.41 18H6.59l-.114.44a.75.75 0 01-1.452-.38L5.822 15H4.75A2.75 2.75 0 012 12.25V3.5h-.25A.75.75 0 011 2.75zM7.373 15l-.391 1.5h6.037l-.392-1.5H7.373zm7.49-8.931a.75.75 0 01-.175 1.046 19.326 19.326 0 00-3.398 3.098.75.75 0 01-1.097.04L8.5 8.561l-2.22 2.22a.75.75 0 11-1.06-1.06l2.75-2.75a.75.75 0 011.06 0l1.664 1.663a20.786 20.786 0 013.122-2.74.75.75 0 011.046.175z" clip-rule="evenodd" />
					</svg>
					Connectors
				</button>
				<div class="border-t border-brand-navy/8"></div>
				<button
					type="button"
					class="flex w-full cursor-pointer items-center gap-2.5 border-0 bg-white px-4 py-2.5 text-left font-body text-sm text-red-600 hover:bg-red-50"
					onclick={handleSignOut}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4">
						<path fill-rule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clip-rule="evenodd" />
						<path fill-rule="evenodd" d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z" clip-rule="evenodd" />
					</svg>
					Sign out
				</button>
			</div>
		{/if}
	</div>
{/if}
