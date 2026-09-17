// SPDX-FileCopyrightText: 2026 Marlon W (Mawoka)
// SPDX-FileCopyrightText: 2026 Roberto Pizarro Diaz
//
// SPDX-License-Identifier: MPL-2.0

import type { Socket } from 'socket.io-client';
import type { ActivityPhase } from '$lib/play/activity/types';

/**
 * Class that encapsulates all the socket calls related to game controls for the admin page.
 * Still in development, but it will be used to avoid having socket calls directly in the svelte files, and to have a single place to manage all the game controls related socket calls.
 */
export class SocketGameControls {
	socket: Socket;

	constructor(socket: Socket) {
		this.socket = socket;
	}

	set_question_number(q_number: number) {
		this.socket.emit('set_question_number', q_number.toString());
	}

	start_deliberation_question(question_index: number) {
		this.socket.emit('start_deliberation_question', { question_index });
	}

	set_activity_phase(question_index: number, phase: ActivityPhase, duration_seconds?: number) {
		this.socket.emit('set_activity_phase', {
			question_index,
			phase,
			...(duration_seconds ? { duration_seconds } : {})
		});
	}

	get_activity_state(question_index: number) {
		this.socket.emit('get_activity_state', { question_index });
	}

	get_activity_results(question_index: number) {
		this.socket.emit('get_activity_results', { question_index });
	}

	get_question_results(game_id: string, question_number: number) {
		this.socket.emit('get_question_results', {
			game_id,
			question_number
		});
	}

	show_solutions() {
		this.socket.emit('show_solutions', {});
	}

	get_final_results() {
		this.socket.emit('get_final_results', {});
	}

	start_game() {
		this.socket.emit('start_game', '');
	}

	kick_player(username: string, players: any[]) {
		this.socket.emit('kick_player', { username: username });

		for (let i = 0; i < players.length; i++) {
			console.log(players[i].username, username);
			if (players[i].username === username) {
				players.splice(i, 1);
				break;
			}
		}
		return players;
	}
}
