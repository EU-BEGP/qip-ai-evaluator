import { Component } from '@angular/core';
import config from '../../config.json'

@Component({
  selector: 'app-footer-component',
  imports: [],
  templateUrl: './footer-component.html',
  styleUrl: './footer-component.css',
})
export class FooterComponent {
  acronym: string = config.organizationData.acronym;
  version: string = config.version;

  getCurrentYear(): number {
    return new Date().getFullYear();
  }
}
