import { Component } from '@angular/core';
import { FormGroup, FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card'; 
import { Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth-service';
import { AccountCredentials } from '../../interfaces/account-credentials';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-login',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule
  ],
  providers: [ToastrService],
  templateUrl: './login.html',
  styleUrl: './login.css',
  standalone: true
})
export class LoginComponent {
  hide: boolean = true;

  loginForm = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
    password: new FormControl('', [
      Validators.required,
      Validators.minLength(8),
    ]),
  });

  constructor(
    private authService: AuthService,
    private toastr: ToastrService,
    private router: Router
  ) { }

  ngOnInit(): void {
    if (localStorage.getItem('token')) {
      this.router.navigateByUrl('modules');
    }
  }

  get emailControl() {
    return this.loginForm.controls['email'];
  }

  get passwordControl() {
    return this.loginForm.controls['password'];
  }

  onSubmit(): void {
    if (this.loginForm.valid) {
      const account: AccountCredentials = {
        email: this.emailControl.value!,
        password: this.passwordControl.value!,
      };
      this.authService.login(account).subscribe((response) => {
        if (response != undefined) {
          this.checkReturnUrl();
        }
      });
    } else {
      this.toastr.error(
        'Please, complete correctly the information.',
        'Invalid action'
      );
    }
  }

  getEmailErrorMessage(): string {
    if (this.emailControl.hasError('required'))
      return 'You must enter an email.';

    return this.emailControl.hasError('email') ? 'Not a valid email.' : '';
  }

  getPasswordErrorMessage(): string {
    if (this.passwordControl.hasError('required')) {
      return 'You must enter a password.';
    }

    return this.passwordControl.hasError('minlength')
      ? 'Password must have at least 8 characters.'
      : '';
  }

  checkReturnUrl() {
    let params = new URLSearchParams(document.location.search);
    let returnUrl = params.get('return-url');

    if (returnUrl) this.router.navigateByUrl(returnUrl);
    else {
      this.router.navigateByUrl('modules');
    }
  }
}
