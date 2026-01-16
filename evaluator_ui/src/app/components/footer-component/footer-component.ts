// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

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
