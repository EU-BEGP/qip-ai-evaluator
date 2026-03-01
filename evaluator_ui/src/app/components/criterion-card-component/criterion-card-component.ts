// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import {
  Component,
  EventEmitter,
  Input,
  Output,
  OnInit,
  ElementRef,
  Renderer2,
  OnDestroy,
} from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

@Component({
  standalone: true,
  selector: 'app-criterion-card-component',
  imports: [MatCardModule, CommonModule, MatButtonModule],
  templateUrl: './criterion-card-component.html',
  styleUrls: ['./criterion-card-component.css'],
})
export class CriterionCardComponent implements OnInit, OnDestroy {
  @Input() question: string = '';
  @Input() description: string = '';
  @Input() buttons: Array<{
    label: string;
    value?: any;
    state?: boolean;
    disabled?: boolean;
  }> = [];
  @Input() hasAI: boolean = false;
  @Input() hasNote: boolean = false;
  @Input() peerNote: string = '';
  @Input() aiLoading: boolean = false;
  private _suggestion?: { result: string; badge: string } | null = null;

  @Input()
  set suggestion(value: { result: string; badge: string } | null | undefined) {
    this._suggestion = value ?? null;

    this.showSuggestion = !!this._suggestion;
    if (this.showSuggestion) {
      this.startAutoCloseTimer();
      this.addDocumentListeners();
    } else {
      this.clearAutoCloseTimer();
      this.removeDocumentListeners();
    }
  }
  get suggestion() {
    return this._suggestion;
  }

  showSuggestion: boolean = false;

  displayedSuggestionText: string = '';
  private streamIntervalId: any = null;
  private streamIndex: number = 0;
  isStreaming: boolean = false;
  private streamSpeedMs: number = 20; // ms per character

  // auto-close timer (ms)
  private autoCloseMs: number = 10000;
  private autoCloseTimerId: any = null;
  private autoCloseRemaining: number = 0;
  private autoCloseStart: number = 0;

  private removeDocClickListener: (() => void) | null = null;
  private removeDocKeyListener: (() => void) | null = null;

  @Output() buttonClick = new EventEmitter<{ value: any }>();
  @Output() aiClick = new EventEmitter<void>();
  @Output() noteFill = new EventEmitter<{ note: string }>();

  constructor(
    private el: ElementRef,
    private renderer: Renderer2,
  ) {}

  ngOnInit(): void {}

  onButtonClick(
    btn: { label: string; value?: any; state?: boolean; disabled?: boolean },
    event: MouseEvent,
  ) {
    event.stopPropagation();
    if (!btn.state) {
      this.buttons.forEach((b) => (b.state = false));
      btn.state = !btn.state;
    }
    if (!btn.disabled) {
      this.buttonClick.emit({ value: btn.value ?? btn.label });
    }
  }

  onNoteFill(event: Event) {
    event.stopPropagation();
    const target = event.target as HTMLInputElement;
    this.noteFill.emit({ note: target.value });
  }

  closeSuggestion(event: MouseEvent) {
    event.stopPropagation();
    this.showSuggestion = false;
  }

  onAiClick(event: MouseEvent) {
    event.stopPropagation();
    if (this._suggestion) {
      this.showSuggestion = true;
      this.startAutoCloseTimer();
      this.addDocumentListeners();
      this.startStreamingSuggestion();
      return;
    }
    this.aiClick.emit();
  }

  startAutoCloseTimer() {
    this.clearAutoCloseTimer();
    this.autoCloseRemaining = this.autoCloseMs;
    this.autoCloseStart = Date.now();
    this.autoCloseTimerId = setTimeout(() => {
      this.showSuggestion = false;
      this.stopStreamingSuggestion();
      this.clearAutoCloseTimer();
      this.removeDocumentListeners();
    }, this.autoCloseRemaining);
  }

  clearAutoCloseTimer() {
    if (this.autoCloseTimerId) {
      clearTimeout(this.autoCloseTimerId);
      this.autoCloseTimerId = null;
    }
  }

  pauseAutoCloseTimer() {
    if (!this.autoCloseTimerId) return;
    const elapsed = Date.now() - this.autoCloseStart;
    this.autoCloseRemaining = Math.max(0, this.autoCloseRemaining - elapsed);
    clearTimeout(this.autoCloseTimerId);
    this.autoCloseTimerId = null;
  }

  // streaming controls
  private startStreamingSuggestion() {
    this.stopStreamingSuggestion();
    if (!this._suggestion || !this._suggestion.result) {
      this.displayedSuggestionText = '';
      this.isStreaming = false;
      return;
    }
    const txt = this._suggestion.result || '';
    this.displayedSuggestionText = '';
    this.streamIndex = 0;
    this.isStreaming = true;
    this.streamIntervalId = setInterval(() => {
      if (this.streamIndex >= txt.length) {
        this.stopStreamingSuggestion();
        return;
      }
      this.displayedSuggestionText += txt.charAt(this.streamIndex);
      this.streamIndex += 1;
    }, this.streamSpeedMs);
  }

  private stopStreamingSuggestion() {
    if (this.streamIntervalId) {
      clearInterval(this.streamIntervalId);
      this.streamIntervalId = null;
    }
    this.isStreaming = false;
  }

  pauseStreaming() {
    if (!this.streamIntervalId) return;
    clearInterval(this.streamIntervalId);
    this.streamIntervalId = null;
  }

  resumeStreaming() {
    if (this.streamIntervalId) return;
    if (!this._suggestion) return;
    const txt = this._suggestion.result || '';
    if (this.streamIndex >= txt.length) return;
    this.streamIntervalId = setInterval(() => {
      if (this.streamIndex >= txt.length) {
        this.stopStreamingSuggestion();
        return;
      }
      this.displayedSuggestionText += txt.charAt(this.streamIndex);
      this.streamIndex += 1;
    }, this.streamSpeedMs);
    this.isStreaming = true;
  }

  resumeAutoCloseTimer() {
    if (this.autoCloseTimerId || this.autoCloseRemaining <= 0) return;
    this.autoCloseStart = Date.now();
    this.autoCloseTimerId = setTimeout(() => {
      this.showSuggestion = false;
      this.clearAutoCloseTimer();
      this.removeDocumentListeners();
    }, this.autoCloseRemaining);
  }

  private addDocumentListeners() {
    if (this.removeDocClickListener || this.removeDocKeyListener) return;
    this.removeDocClickListener = this.renderer.listen(
      'document',
      'click',
      (e: Event) => {
        if (!this.el.nativeElement.contains(e.target)) {
          this.showSuggestion = false;
          this.clearAutoCloseTimer();
          this.removeDocumentListeners();
        }
      },
    );

    this.removeDocKeyListener = this.renderer.listen(
      'document',
      'keydown',
      (e: KeyboardEvent) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
          this.showSuggestion = false;
          this.clearAutoCloseTimer();
          this.removeDocumentListeners();
        }
      },
    );
  }

  private removeDocumentListeners() {
    if (this.removeDocClickListener) {
      this.removeDocClickListener();
      this.removeDocClickListener = null;
    }
    if (this.removeDocKeyListener) {
      this.removeDocKeyListener();
      this.removeDocKeyListener = null;
    }
  }

  ngOnDestroy(): void {
    this.clearAutoCloseTimer();
    this.removeDocumentListeners();
  }
}
