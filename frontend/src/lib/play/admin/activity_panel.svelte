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
		FacilitationMode,
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
	let player_count = $state(0);
	let facilitation_mode = $state(FacilitationMode.WAITING);
	let error = $state('');
	let discussion_seconds = $state(120);

	const isMicrogroup = $derived(facilitation_mode === FacilitationMode.MICROGROUP);
	const isClassroom = $derived(facilitation_mode === FacilitationMode.CLASSROOM);

	const requestSnapshot = () => {
		socket_game_controls.get_activity_state(question_index);
		socket_game_controls.get_activity_results(question_index);
	};

	onMount(() => {
		const onActivityState = (data: ActivityStateEvent) => {
			if (!data.state || data.state.question_index !== question_index) return;
			state = data.state;
			player_count = data.player_count ?? 0;
			facilitation_mode = data.facilitation_mode ?? FacilitationMode.WAITING;
			progress = {
				question_index,
				phase: data.state.phase,
				response_count: data.response_count ?? 0,
				player_count: data.player_count ?? 0,
				facilitation_mode: data.facilitation_mode ?? FacilitationMode.WAITING
			};
		};

		const onPhaseChanged = (data: ActivityState) => {
			if (data.question_index !== question_index) return;
			state = data;
			error = '';
			requestSnapshot();
		};

		const onProgress = (data: ActivityProgress) => {
			if (data.question_index !== question_index) return;
			progress = data;
			player_count = data.player_count;
			facilitation_mode = data.facilitation_mode;
			socket_game_controls.get_activity_results(question_index);
		};

		const onResults = (data: ActivityResults) => {
			if (data.question_index !== question_index) return;
			results = data;
			player_count = data.player_count;
			facilitation_mode = data.facilitation_mode;
		};

		const onActivityError = (data: { code?: string }) => {
			error = data?.code ?? 'activity_error';
		};

		socket.on('activity_state', onActivityState);
		socket.on('activity_phase_changed', onPhaseChanged);
		socket.on('activity_progress', onProgress);
		socket.on('activity_results', onResults);
		socket.on('activity_error', onActivityError);
		requestSnapshot();

		return () => {
			socket.off('activity_state', onActivityState);
			socket.off('activity_phase_changed', onPhaseChanged);
			socket.off('activity_progress', onProgress);
			socket.off('activity_results', onResults);
			socket.off('activity_error', onActivityError);
		};
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
			[ActivityPhase.INITIAL_RESPONSE]: 'R1 · respuesta individual',
			[ActivityPhase.DISCUSSION]: 'Discusión',
			[ActivityPhase.SECOND_RESPONSE]: 'R2 · respuesta individual',
			[ActivityPhase.REFLECTION]: 'Reflexión',
			[ActivityPhase.RESULTS]: 'Resultados agregados'
		};
		return labels[state.phase];
	});

	const facilitationLabel = $derived.by(() => {
		if (isMicrogroup) return 'Microgrupo · 1–3 participantes';
		if (isClassroom) return 'Aula · 4+ participantes';
		return 'Esperando participantes';
	});

	const r1_total = $derived(
		Object.values(results?.initial_counts ?? {}).reduce((sum, count) => sum + count, 0)
	);
	const r2_total = $derived(
		Object.values(results?.second_counts ?? {}).reduce((sum, count) => sum + count, 0)
	);
	const reflection_total = $derived(results?.reflection_count ?? 0);
	const participant_total = $derived(results?.player_count ?? player_count);
	const answer_choices = $derived.by(() => {
		const configured = (quiz_data.questions[question_index]?.answers ?? []).map((answer: any) =>
			String(answer.answer)
		);
		const observed = [
			...Object.keys(results?.initial_counts ?? {}),
			...Object.keys(results?.second_counts ?? {})
		];
		return Array.from(new Set([...configured, ...observed]));
	});
	const responsePhase = $derived(
		state?.phase === ActivityPhase.INITIAL_RESPONSE ||
			state?.phase === ActivityPhase.SECOND_RESPONSE ||
			state?.phase === ActivityPhase.REFLECTION
	);
</script>

<div class="fixed top-0 z-30 w-full border-b border-slate-200 bg-white px-4 py-2 text-slate-900 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
	<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
		<div class="mr-auto">
			<p class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
				ICCI · Espacio de debate
			</p>
			<div class="flex flex-wrap items-center gap-2">
				<p class="font-semibold">{phaseLabel}</p>
				<span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold dark:bg-slate-800">
					{facilitationLabel}
				</span>
			</div>
		</div>

		{#if responsePhase && progress && state && progress.phase === state.phase}
			<span class="rounded-full bg-slate-100 px-3 py-1 text-sm dark:bg-slate-800">
				{progress.response_count} de {progress.player_count} respuestas
			</span>
		{/if}

		{#if state?.phase === ActivityPhase.INITIAL_RESPONSE}
			<label class="flex items-center gap-2 text-sm">
				Discusión
				<input
					class="w-20 rounded border border-slate-300 bg-transparent px-2 py-1"
					type="number"
					min="30"
					max="3600"
					step="30"
					bind:value={discussion_seconds}
				/>
				s
			</label>
		{/if}

		{#if state && state.phase !== ActivityPhase.RESULTS}
			<button type="button" class="admin-button" onclick={nextPhase}>
				{state.phase === ActivityPhase.INITIAL_RESPONSE
					? 'Iniciar discusión'
					: state.phase === ActivityPhase.DISCUSSION
						? 'Abrir R2'
						: state.phase === ActivityPhase.SECOND_RESPONSE
							? 'Abrir reflexión'
							: 'Mostrar resultados'}
			</button>
		{/if}

		{#if state?.phase === ActivityPhase.RESULTS}
			{#if hasNext}
				<button
					type="button"
					class="admin-button"
					onclick={() => socket_game_controls.set_question_number(nextIndex)}
				>
					Siguiente pregunta
				</button>
				{#if nextIsVoting}
					<button
						type="button"
						class="admin-button"
						onclick={() => socket_game_controls.start_deliberation_question(nextIndex)}
					>
						Siguiente como debate
					</button>
				{/if}
			{:else}
				<button
					type="button"
					class="admin-button"
					onclick={() => socket_game_controls.get_final_results()}
				>
					Finalizar sesión
				</button>
			{/if}
		{/if}
	</div>
	{#if error}
		<p class="mx-auto mt-1 max-w-7xl text-sm text-red-600">Error de actividad: {error}</p>
	{/if}
</div>

<div class="mx-auto max-w-7xl px-4 pt-24 pb-10 text-slate-900 dark:text-slate-100">
	{#if !state}
		<div class="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
			Esperando estado de la actividad…
		</div>
	{:else}
		<div class="grid gap-4 md:grid-cols-4">
			<div class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 md:col-span-4 lg:col-span-2">
				<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Pregunta en curso</p>
				<h2 class="mt-2 text-2xl font-semibold">
					{@html quiz_data.questions[question_index].question}
				</h2>
			</div>
			<div class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold text-slate-500">R1 recibidas</p>
				<p class="mt-2 text-3xl font-semibold">{r1_total} <span class="text-base font-normal text-slate-500">de {participant_total}</span></p>
			</div>
			<div class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold text-slate-500">R2 recibidas</p>
				<p class="mt-2 text-3xl font-semibold">{r2_total} <span class="text-base font-normal text-slate-500">de {participant_total}</span></p>
			</div>
		</div>

		{#if isMicrogroup && state.phase === ActivityPhase.DISCUSSION}
			<section class="mt-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Facilitación adaptativa · microgrupo</p>
				<div class="mt-3 grid gap-3 md:grid-cols-3">
					<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
						<p class="font-semibold">1 · Exposición</p>
						<p class="mt-1 text-sm text-slate-600 dark:text-slate-300">Cada participante presenta su razón principal sin interrupciones.</p>
					</div>
					<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
						<p class="font-semibold">2 · Contraste</p>
						<p class="mt-1 text-sm text-slate-600 dark:text-slate-300">Cuando haya más de una persona, se pregunta o responde a un argumento ajeno.</p>
					</div>
					<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
						<p class="font-semibold">3 · Preparación R2</p>
						<p class="mt-1 text-sm text-slate-600 dark:text-slate-300">Cada participante identifica razones que mantiene o revisa.</p>
					</div>
				</div>
			</section>
		{/if}

		{#if isClassroom && state.phase === ActivityPhase.DISCUSSION}
			<section class="mt-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold uppercase tracking-wide text-slate-500">Facilitación adaptativa · aula</p>
				<p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
					La actividad mantiene el flujo de clase y no aplica el protocolo acotado de microgrupo. La formación automática de pares o subgrupos puede incorporarse como una capa posterior.
				</p>
			</section>
		{/if}

		{#if state.phase === ActivityPhase.REFLECTION}
			<section class="mt-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
				<p class="text-sm font-semibold text-slate-500">Reflexiones recibidas</p>
				<p class="mt-2 text-3xl font-semibold">
					{reflection_total}
					<span class="text-base font-normal text-slate-500">de {participant_total}</span>
				</p>
			</section>
		{/if}

		{#if state.phase === ActivityPhase.RESULTS && results}
			<div class="mt-4 grid gap-4 lg:grid-cols-2">
				<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
					<h2 class="text-xl font-semibold">R1 y R2 · distribución agregada</h2>
					<div class="mt-4 grid grid-cols-2 gap-4">
						<div>
							<p class="text-sm font-semibold text-slate-500">R1</p>
							{#each answer_choices as answer}
								<p class="mt-1"><strong>{results.initial_counts[answer] ?? 0}</strong> · {answer}</p>
							{/each}
						</div>
						<div>
							<p class="text-sm font-semibold text-slate-500">R2</p>
							{#each answer_choices as answer}
								<p class="mt-1"><strong>{results.second_counts[answer] ?? 0}</strong> · {answer}</p>
							{/each}
						</div>
					</div>
					<div class="mt-5 grid grid-cols-2 gap-3">
						<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
							<span class="text-2xl font-semibold">{results.stance.maintained}</span><br />
							<span class="text-sm">mantuvieron alternativa</span>
						</div>
						<div class="rounded-xl bg-slate-100 p-4 dark:bg-slate-800">
							<span class="text-2xl font-semibold">{results.stance.changed}</span><br />
							<span class="text-sm">cambiaron alternativa</span>
						</div>
					</div>
				</section>

				<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
					<h2 class="text-xl font-semibold">Variación de convicción</h2>
					<div class="mt-4 space-y-2">
						<p><strong>{results.confidence_change.increased}</strong> aumentaron</p>
						<p><strong>{results.confidence_change.decreased}</strong> disminuyeron</p>
						<p><strong>{results.confidence_change.unchanged}</strong> mantuvieron</p>
					</div>
					<p class="mt-4 text-sm text-slate-500">
						Comparación descriptiva de participantes con R1 y R2 registradas: {results.matched_participants}.
					</p>
					<p class="mt-2 text-sm text-slate-500">
						Reflexiones registradas: {results.reflection_count}. El panel no expone textos ni identidades individuales.
					</p>
				</section>

				<section class="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 lg:col-span-2">
					<h2 class="text-xl font-semibold">Matriz de transición R1 → R2</h2>
					<p class="mt-1 text-sm text-slate-500">
						Describe desplazamientos entre alternativas; mantener o cambiar no se interpreta como mejor o peor.
					</p>
					<div class="mt-4 overflow-x-auto">
						<table class="min-w-full border-collapse text-center text-sm">
							<thead>
								<tr>
									<th class="border-b border-slate-200 p-2 text-left dark:border-slate-700">R1 ↓ / R2 →</th>
									{#each answer_choices as to}
										<th class="border-b border-slate-200 p-2 dark:border-slate-700">{to}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each answer_choices as from}
									<tr>
										<th class="border-t border-slate-200 p-2 text-left dark:border-slate-700">{from}</th>
										{#each answer_choices as to}
											<td class="border-t border-slate-200 p-2 font-semibold dark:border-slate-700">
												{results.transitions[from]?.[to] ?? 0}
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</section>
			</div>
		{:else if state.phase === ActivityPhase.RESULTS}
			<div class="mt-4 rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
				Calculando resultados agregados…
			</div>
		{/if}
	{/if}
</div>
