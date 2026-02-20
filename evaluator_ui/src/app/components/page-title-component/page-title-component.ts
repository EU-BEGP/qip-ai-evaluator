import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-page-title-component',
  imports: [
    MatIconModule
  ],
  templateUrl: './page-title-component.html',
  styleUrl: './page-title-component.css',
})
export class PageTitleComponent {
  @Input() title: string = '';
  @Input() icon: string = '';
}
