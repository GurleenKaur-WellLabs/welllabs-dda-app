<script>
	import { goto } from '$app/navigation';
	import { register } from '$lib/modules/accounts/api.js';
	import { session } from '$lib/shared/session.svelte.js';
	import AuthHeader from '$lib/shared/components/auth/AuthHeader.svelte';
	import ContourBackground from '$lib/shared/components/landing/ContourBackground.svelte';

	let name = $state('');
	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		if (!name.trim() || !email.trim() || password.length < 8) return;
		submitting = true;
		error = '';
		try {
			const user = await register(email.trim(), name.trim(), password);
			session.setUser(user);
			goto('/home');
		} catch (err) {
			error = String(err.message ?? err);
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Create account · DDA</title>
</svelte:head>

<div class="relative flex min-h-screen items-center justify-center overflow-hidden bg-void px-4 font-body">
	<ContourBackground intensity="ambient" />

	<div class="relative z-10 w-full max-w-sm rounded-[20px] border border-hairline bg-panel p-8 shadow-glass">
		<span class="font-mono text-[11px] uppercase tracking-[0.2em] text-diagnose">Get started</span>
		<h1 class="mt-2 font-display text-2xl text-ink">Create an account</h1>
		<p class="mt-1 font-body text-[13px] text-ink-dim">Set up your watershed workspace.</p>

		<form onsubmit={handleSubmit} class="mt-7 flex flex-col gap-4">
			<div>
				<label class="mb-1.5 block font-mono text-[11px] uppercase tracking-wide text-ink-faint" for="name">
					Name
				</label>
				<input
					id="name"
					type="text"
					required
					class="w-full rounded-lg border border-hairline bg-panel-raised px-3 py-2.5 font-body text-[14px] text-ink placeholder:text-ink-faint focus:border-diagnose/60 focus:outline-none focus:ring-1 focus:ring-diagnose/40"
					bind:value={name}
					autocomplete="name"
				/>
			</div>
			<div>
				<label class="mb-1.5 block font-mono text-[11px] uppercase tracking-wide text-ink-faint" for="email">
					Email
				</label>
				<input
					id="email"
					type="email"
					required
					class="w-full rounded-lg border border-hairline bg-panel-raised px-3 py-2.5 font-body text-[14px] text-ink placeholder:text-ink-faint focus:border-diagnose/60 focus:outline-none focus:ring-1 focus:ring-diagnose/40"
					bind:value={email}
					autocomplete="email"
				/>
			</div>
			<div>
				<label class="mb-1.5 block font-mono text-[11px] uppercase tracking-wide text-ink-faint" for="password">
					Password
				</label>
				<input
					id="password"
					type="password"
					required
					minlength="8"
					class="w-full rounded-lg border border-hairline bg-panel-raised px-3 py-2.5 font-body text-[14px] text-ink placeholder:text-ink-faint focus:border-diagnose/60 focus:outline-none focus:ring-1 focus:ring-diagnose/40"
					bind:value={password}
					autocomplete="new-password"
				/>
				<p class="m-0 mt-1.5 font-mono text-[10px] text-ink-faint">At least 8 characters.</p>
			</div>

			{#if error}
				<p class="m-0 font-mono text-[12px] text-red-400">{error}</p>
			{/if}

			<button
				type="submit"
				class="mt-2 cursor-pointer rounded-full bg-brand-blue px-4 py-2.5 font-body text-[14px] font-semibold text-white shadow-glass transition-all duration-200 hover:bg-brand-deep disabled:cursor-not-allowed disabled:opacity-50"
				disabled={submitting || !name.trim() || !email.trim() || password.length < 8}
			>
				{submitting ? 'Creating account…' : 'Create account'}
			</button>
		</form>

		<p class="mt-6 text-center font-body text-[13px] text-ink-dim">
			Already have an account?
			<a href="/login" class="font-medium text-diagnose hover:underline">Sign in</a>
		</p>
	</div>
</div>