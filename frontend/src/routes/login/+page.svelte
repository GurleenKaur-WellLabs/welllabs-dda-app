<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { login } from '$lib/modules/accounts/api.js';
	import { session } from '$lib/shared/session.svelte.js';

	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let error = $state('');

	async function handleSubmit(e) {
		e.preventDefault();
		if (!email.trim() || !password) return;
		submitting = true;
		error = '';
		try {
			const user = await login(email.trim(), password);
			session.setUser(user);
			const next = page.url.searchParams.get('next') || '/home';
			goto(next);
		} catch (err) {
			error = String(err.message ?? err);
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Sign in · DDA Product</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-brand-sky/10 px-4 font-body">
	<div class="w-full max-w-sm rounded-2xl border border-brand-navy/10 bg-white p-8 shadow-sm">
		<h1 class="m-0 mb-1 font-headline text-2xl font-semibold text-brand-navy">Sign in</h1>
		<p class="m-0 mb-6 text-sm text-brand-steel">Welcome back to DDA Product.</p>

		<form onsubmit={handleSubmit} class="flex flex-col gap-4">
			<div>
				<label class="mb-1 block text-sm font-medium text-brand-navy" for="email">Email</label>
				<input
					id="email"
					type="email"
					required
					class="w-full rounded border border-brand-navy/20 px-3 py-2 font-body"
					bind:value={email}
					autocomplete="email"
				/>
			</div>
			<div>
				<label class="mb-1 block text-sm font-medium text-brand-navy" for="password">Password</label>
				<input
					id="password"
					type="password"
					required
					class="w-full rounded border border-brand-navy/20 px-3 py-2 font-body"
					bind:value={password}
					autocomplete="current-password"
				/>
			</div>

			{#if error}
				<p class="m-0 text-sm text-red-600">{error}</p>
			{/if}

			<button
				type="submit"
				class="mt-1 cursor-pointer rounded bg-brand-blue px-4 py-2 font-body text-white disabled:cursor-not-allowed disabled:opacity-60"
				disabled={submitting || !email.trim() || !password}
			>
				{submitting ? 'Signing in…' : 'Sign in'}
			</button>
		</form>

		<p class="m-0 mt-5 text-center text-sm text-brand-steel">
			Don't have an account?
			<a href="/register" class="font-medium text-brand-blue hover:underline">Register</a>
		</p>
	</div>
</div>
