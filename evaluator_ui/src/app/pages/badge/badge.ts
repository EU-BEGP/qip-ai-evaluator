import { Component } from '@angular/core';
import { BadgeService } from '../../services/badge-service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-badge',
  imports: [],
  templateUrl: './badge.html',
  styleUrls: ['./badge.css'],
})
export class Badge {
  moduleName: string = '';
  badge: string = '';
  teachers: string[] = [];
  rating: number = 0;
  ratingsCount: number = 0;

  constructor(
    private badgeService: BadgeService,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token');
    if (!token) {
      return;
    }

    this.badgeService.retrieveBadgeData(token).subscribe({
      next: (data) => {
        console.log('Badge data:', data);
        this.moduleName = data.module_name;
        this.badge = data.badge;
        this.teachers = data.teachers;
        this.rating = data.rating;
        this.ratingsCount = data.total_reviews;
      },
      error: (err) => {
        console.error('Error retrieving badge data:', err);
      },
    });
  }
}
