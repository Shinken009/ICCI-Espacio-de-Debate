<!--
SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz

SPDX-License-Identifier: MPL-2.0
-->

<script lang="ts">
	import { onMount } from 'svelte';
	import { socket } from '$lib/socket';
	import { QuizQuestionType } from '$lib/quiz_types';
	import { SocketGameControls } from '$lib/play/admin/socket_game_controls.ts';
	import {
		ActivityPhase,
		type ActivityProgress,
		type ActivityResults,
		type ActivityState,
		type ActivityStateEvent
	} from '$lib/play/activity/types';

	interface Props {
		question_index: number;
		quiz_data: any;
		socket_game_controls: SocketGameControls;
	}

	let { question_index, quiz_data, socket_game_controls }: Props = $props();
	let state: ActivityState | null = $state(null);
	let progress: ActivityProgress | null = $state(null);
	let results: ActivityResults | null = $state(null);
	let error = $state('');
	let discussion_seconds = $state(120);

	onMount(() => {
		socket_game_controls.get_activity_state(question_index);
	});

	socket.on('activity_state', (data: ActivityStateEvent) => {
		if (!data.state || data.state.question_index !== question_index) return;
		state = data.state;
	});

	socket.on('activity_phase_changed', (data: ActivityState) => {
		if (data.question_index !== question_index) return;
		state = data;
		error = '';
		if (data.phase === ActivityPhase.RESULTS) {
			socket_game_controls.get_activity_results(question_index);
		}
	});

	socket.on('activity_progress', (data: ActivityProgress) => {
		if (data.question_index !== question_index) return;
		progress = data;
	});

	socket.on('activity_results', (data: ActivityResults) => {
		if (data.question_index !== question_index) return;
		results = data;
	});

	socket.on('activity_error', (data) => {
		error = data?.code ?? 'activity_error';
	});

	const nextPhase = () => {
		if (!state) return;
		if (state.phase === ActivityPhase.INITIAL_RESPONSE) {
			socket_game_controls.set_activity_phase(
				question_index,
				ActivityPhase.DISCUSSION,
				Number(discussion_seconds)
			);
			return;
		}
		if (state.phase === ActivityPhase.DISCUSSION) {
			socket_game_controls.set_activity_phase(question_index, ActivityPhase.SECOND_RESPONSE);
			return;
		}
		if (state.phase === ActivityPhase.SECOND_RESPONSE) {
			socket_game_controls.set_activity_phase(question_index, ActivityPhase.REFLECTION);
			return;
		}
		if (state.phase === ActivityPhase.REFLECTION) {
			socket_game_controls.set_activity_phase(question_index, ActivityPhase.RESULTS);
		}
	};

	const nextIndex = $derived(question_index + 1);
	const hasNext = $derived(nextIndex < quiz_data.questions.length);
	const nextIsVoting = $derived(
		hasNext && quiz_data.questions[nextIndex]?.type === QuizQuestionType.VOTING
	);

	const phaseLabel = $derived.by(() => {
		if (!state) return 'Preparando actividad';
		const labels: Record<ActivityPhase, string> = {
			[ActivityPhase.INITIAL_RESPONSE]: 'Primera respuesta individual',
			[ActivityPhase.DISCUSSION]: 'Discusión entre pares',
			[ActivityPhase.SECOND_RESPONSE]: 'Segunda respuesta individual',
			[ActivityPhase.REFLECTION]: 'Reflexión metacognitiva',
			[ActivityPhase.RESULTS]: 'Resultados agregados'
		};
		return labels[state.phase];
	});
</script>

<div class="fixed top-0 z-30 w-full border-b border-slate-200 bg-white px-4 py-2 text-slate-900 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
	<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
		<div class="mr-auto">
			<p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">ICCI · Espacio de debate</p>
			<p class="font-semibold">{phaseLabel}</p>
		</div>

		{#if progress && state && progress.phase === state.phase}
			<span class="rounded-full bg-slate-100 px-3 py-1 text-sm dark:bg-slate-800">
				{progress.response_count} de {progress.player_count} respuestas
			</span>
		{/if}

		{#if state?.phase === ActivityPhase.INITIAL_RESPONSE}
			<label class="flex items-center gap-2 text-sm">
				Discusión
				<input class="w-20 rounded border border-slate-300 bg-transparent px-2 py-1" type="number" min="30" max="3600" step="30" bind:value={discussion_seconds} />
				s
			</label>
		{/if}

		{#if state && state.phase !== ActivityPhase.RESULTS}
			<button type="button" class="admin-button" onclick={nextPhase}>
				{state.phase === ActivityPhase.INITIAL_RESPONSE
					? 'Iniciar discusión'
					: state.phase === ActivityPhase.DISCUSSION
						? 'Abrir segunda respuesta'
						: state.phase === ActivityPhase.SECOND_RESPONSE
							? 'Abrir reflexión'
							: 'Mostrar resultados'}
			</button>
		{/if}

		{#if state?.phase === ActivityPhase.RESULTS}
			{#if hasNext}
				<button type="button" class="admin-button" onclick={() => socket_game_controls.set_question_number(nextIndex)}>Siguiente pregunta</button>
				{#if nextIsVoting}
					<button type="button" class="admin-button" onclick={() => socket_game_controls.start_deliberation_question(nextIndex)}>Siguiente como debate</button>
				{/if}
			{:else}
				<button type="button" class="admin-button" onclick={() => socket_game_controls.get_final_results()}>Finalizar sesión</button>
			{/if}
		{/if}
	</div>
	{#if error}<p class="mx-auto mt-1 max-w-7xl text-sm text-red-600">Error de actividad: {error}</p>{/if}
</div>

<div class="mx-auto max-w-7xl px-4 pt-24 pb-10 text-slate-900 dark:text-slate-100">
	{#if !state}
		<div class="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
			Esperando estado de la actividad…
		</div>
	{:else if state.phase !== ActivityPhase.RESULTS}
		<div class="grid gap-4 md:grid-cols-3">
			<div class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 md:col-span-2">
				<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Pregunta en curso</p>
				<h2 class="mt-2 text-2xl font-semibold">{@html quiz_data.questions[question_index].question}</h2>
			</div>
			<div class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Seguimiento</p>
				<p class="mt-2 text-3xl font-semibold">{progress?.response_count ?? 0}</p>
				<p class="text-sm text-slate-500">respuestas registradas en esta fase</p>
			</div>
		</div>
	{:else if results}
		<div class="grid gap-4 lg:grid-cols-2">
			<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<h2 class="text-xl font-semibold">Posturas antes y después</h2>
				<div class="mt-4 grid grid-cols-2 gap-4">
					<div>
						<p class="text-sm font-semibold text-slate-500">Ronda 1</p>
						{#each Object.entries(results.initial_counts) as [choice, count]}
							<p class="mt-1"><strong>{count}</strong> · {choice}</p>
						{/each}
					</div>
					<div>
						<p class="text-sm font-semibold text-slate-500">Ronda 2</p>
						{#each Object.entries(results.second_counts) as [choice, count]}
							<p class="mt-1"><strong>{count}</strong> · {choice}</p>
						{/each}
					</div>
				</div>
				<div class="mt-5 grid grid-cols-2 gap-3">
					<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800"><span class="text-2xl font-semibold">{results.stance.maintained}</span><br /><span class="text-sm">mantuvieron postura</span></div>
					<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800"><span class="text-2xl font-semibold">{results.stance.changed}</span><br /><span class="text-sm">cambiaron postura</span></div>
				</div>
			</section>

			<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<h2 class="text-xl font-semibold">Cambio de convicción</h2>
				<div class="mt-4 space-y-2">
					<p><strong>{results.confidence_change.increased}</strong> aumentaron su convicción</p>
					<p><strong>{results.confidence_change.decreased}</strong> disminuyeron su convicción</p>
					<p><strong>{results.confidence_change.unchanged}</strong> la mantuvieron</p>
				</div>
				<p class="mt-4 text-sm text-slate-500">Se comparan únicamente participantes con R1 y R2 registradas: {results.matched_participants}.</p>
			</section>

			<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 lg:col-span-2">
				<h2 class="text-xl font-semibold">Matriz de transiciones</h2>
				<div class="mt-4 overflow-x-auto">
					<table class="min-w-full text-left text-sm">
						<thead><tr><th class="p-2">Desde</th><th class="p-2">Hacia</th><th class="p-2">Personas</th></tr></thead>
						<tbody>
							{#each Object.entries(results.transitions) as [from, destinations]}
								{#each Object.entries(destinations) as [to, count]}
									<tr class="border-t border-slate-200 dark:border-slate-700"><td class="p-2">{from}</td><td class="p-2">{to}</td><td class="p-2 font-semibold">{count}</td></tr>
								{/each}
							{/each}
						</tbody>
					</table>
				</div>
			</section>
		</div>
	{:else}
		<div class="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">Calculando resultados agregados…</div>
	{/if}
</div>
