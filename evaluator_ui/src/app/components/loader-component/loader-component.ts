// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component } from '@angular/core';
import { LoaderService } from '../../services/loader-service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loader-component',
  imports: [
    CommonModule
  ],
  templateUrl: './loader-component.html',
  styleUrl: './loader-component.css',
})
export class LoaderComponent {
  constructor(
    public loaderService: LoaderService
  ) {}
}
