import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('evaluator_ui');

  private storageHandler = (e: StorageEvent) => {
    if (e.key !== 'token') return;

    if (e.newValue !== e.oldValue) {
      window.location.reload();
    }
  };

  ngOnInit(): void {
    window.addEventListener('storage', this.storageHandler);
  }

  ngOnDestroy(): void {
    window.removeEventListener('storage', this.storageHandler);
  }
}
