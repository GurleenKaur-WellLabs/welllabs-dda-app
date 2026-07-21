<script lang="ts">
	import { onMount } from 'svelte';
	import { animate, inView } from 'motion';
	import Nav from '$lib/shared/components/landing/Nav.svelte';
	import Hero from '$lib/shared/components/landing/Hero.svelte';
	import WorkspacePanels from '$lib/shared/components/landing/WorkspacePanels.svelte';
	import ContinueWorking from '$lib/shared/components/landing/ContinueWorking.svelte';
	import MetricsOverview from '$lib/shared/components/landing/MetricsOverview.svelte';
	import ProjectGallery from '$lib/shared/components/landing/ProjectGallery.svelte';
	import Footer from '$lib/shared/components/landing/Footer.svelte';

	onMount(() => {
		const reveals = document.querySelectorAll<HTMLElement>('[data-reveal]');
		reveals.forEach((el) => {
			el.style.opacity = '0';
			inView(
				el,
				() => {
					animate(el, { opacity: [0, 1], transform: ['translateY(24px)', 'translateY(0)'] }, { duration: 0.8, easing: [0.16, 1, 0.3, 1] });
				},
				{ margin: '-10% 0px -10% 0px' }
			);
		});
	});
</script>

<svelte:head>
	<title>DDA</title>
	<meta name="description" content="One workspace. Every watershed. Every decision." />
</svelte:head>

<Nav />

<main class="bg-void">
	<Hero />

	<div data-reveal>
		<WorkspacePanels />
	</div>

	<div data-reveal>
		<MetricsOverview />
	</div>
	<Footer />
</main>
